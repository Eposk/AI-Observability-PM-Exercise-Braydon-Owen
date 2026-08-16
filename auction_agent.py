"""Minimal LLM agent: an auction-closing assistant.

Loop: send messages + tool definitions to Claude -> handle tool_use blocks ->
execute the matching Python function -> append tool_result -> repeat until
Claude returns a final text response (or MAX_ITERATIONS is hit).
"""

import json
import logging
import os
import uuid

from dotenv import load_dotenv

load_dotenv()

# Quiets routine "failed to export, will retry" warnings when no local Observe
# Agent/collector is running (e.g. running this agent on a machine that isn't
# instrumented for telemetry). The agent itself still works fine either way.
logging.getLogger("opentelemetry.exporter.otlp.proto.http.trace_exporter").setLevel(logging.ERROR)

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from traceloop.sdk import Traceloop
from traceloop.sdk.decorators import task, workflow

from llm_explorer_processor import LLMExplorerSpanProcessor

_otlp_traces_endpoint = os.environ.get("TRACELOOP_BASE_URL", "http://localhost:4318") + "/v1/traces"

Traceloop.init(
    app_name="auction-agent",
    telemetry_enabled=False,
    processor=LLMExplorerSpanProcessor(OTLPSpanExporter(endpoint=_otlp_traces_endpoint)),
)

from anthropic import Anthropic

from mock_data import ITEMS

MODEL = "claude-sonnet-4-5-20250929"
MAX_ITERATIONS = 8

SYSTEM_PROMPT = """You are an auction-closing assistant for NewCo Auctions.

When asked to close out an auction or determine a winner, follow this process:
1. Call get_highest_valid_bid to find the highest bid and bidder for the item.
2. Call check_reserve_met to confirm that bid clears the item's reserve price.
3. Only if the reserve is met, call generate_invoice to produce the final bill.

If the reserve is not met, or there are no bids, explain that clearly to the
user and do NOT generate an invoice. If the user references an item without
a clear item ID (e.g. a nickname or partial description), ask them to
clarify the item ID rather than guessing one. Do not fabricate bid amounts,
bidder IDs, or invoice totals -- always use the tools to look up real data."""

TOOLS = [
    {
        "name": "get_highest_valid_bid",
        "description": (
            "Look up all bids submitted for an auction item and return the "
            "highest bid amount and the bidder who placed it. Returns an "
            "error if the item_id does not exist, or an empty result if the "
            "item has no bids."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "string",
                    "description": "The auction item's ID, e.g. 'A-100'.",
                }
            },
            "required": ["item_id"],
        },
    },
    {
        "name": "check_reserve_met",
        "description": (
            "Check whether a given bid amount meets or exceeds the item's "
            "reserve (minimum acceptable) price."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "string",
                    "description": "The auction item's ID, e.g. 'A-100'.",
                },
                "bid_amount": {
                    "type": "number",
                    "description": "The bid amount to check against the reserve.",
                },
            },
            "required": ["item_id", "bid_amount"],
        },
    },
    {
        "name": "generate_invoice",
        "description": (
            "Generate a final invoice for the winning bidder, applying a "
            "10% buyer's premium on top of the winning bid. Only call this "
            "after confirming the reserve was met."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "item_id": {"type": "string"},
                "winning_bidder_id": {"type": "string"},
                "bid_amount": {"type": "number"},
            },
            "required": ["item_id", "winning_bidder_id", "bid_amount"],
        },
    },
]

BUYERS_PREMIUM_RATE = 0.10


@task(name="get_highest_valid_bid")
def get_highest_valid_bid(item_id: str) -> dict:
    if item_id not in ITEMS:
        return {"error": f"Unknown item_id '{item_id}'. No such auction item exists."}

    bids = ITEMS[item_id]["bids"]
    if not bids:
        return {"item_id": item_id, "highest_bid": None, "bidder_id": None,
                 "message": "No bids have been placed on this item."}

    top = max(bids, key=lambda b: b["amount"])
    return {"item_id": item_id, "highest_bid": top["amount"], "bidder_id": top["bidder_id"]}


@task(name="check_reserve_met")
def check_reserve_met(item_id: str, bid_amount: float) -> dict:
    if item_id not in ITEMS:
        return {"error": f"Unknown item_id '{item_id}'. No such auction item exists."}

    reserve = ITEMS[item_id]["reserve"]
    return {
        "item_id": item_id,
        "reserve": reserve,
        "bid_amount": bid_amount,
        "reserve_met": bid_amount >= reserve,
    }


@task(name="generate_invoice")
def generate_invoice(item_id: str, winning_bidder_id: str, bid_amount: float) -> dict:
    if item_id not in ITEMS:
        return {"error": f"Unknown item_id '{item_id}'. No such auction item exists."}

    premium = round(bid_amount * BUYERS_PREMIUM_RATE, 2)
    total = round(bid_amount + premium, 2)
    return {
        "item_id": item_id,
        "item_name": ITEMS[item_id]["name"],
        "winning_bidder_id": winning_bidder_id,
        "winning_bid": bid_amount,
        "buyers_premium": premium,
        "total_due": total,
    }


TOOL_FUNCTIONS = {
    "get_highest_valid_bid": get_highest_valid_bid,
    "check_reserve_met": check_reserve_met,
    "generate_invoice": generate_invoice,
}


@workflow(name="auction_agent_run")
def run_agent(
    user_message: str,
    verbose: bool = True,
    api_key: str = None,
    model: str = None,
    timeout: float = None,
    max_iterations: int = None,
) -> dict:
    """Runs the agent loop for a single user message. Returns the full transcript.

    api_key/model/timeout/max_iterations let error_scenarios.py override normal
    config to deliberately trigger auth, not-found, timeout, or budget errors.
    """
    client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"), timeout=timeout)
    model = model or MODEL
    max_iterations = max_iterations or MAX_ITERATIONS

    Traceloop.set_association_properties({"conversation_id": str(uuid.uuid4())})

    messages = [{"role": "user", "content": user_message}]
    transcript = {"user_message": user_message, "system_prompt": SYSTEM_PROMPT, "turns": []}

    if verbose:
        print(f"\n{'=' * 80}\nUSER: {user_message}\n{'=' * 80}")

    for iteration in range(max_iterations):
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        turn_record = {"iteration": iteration, "stop_reason": response.stop_reason, "content": []}

        assistant_content = []
        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
                turn_record["content"].append({"type": "text", "text": block.text})
                if verbose:
                    print(f"\n[assistant text] {block.text}")
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use", "id": block.id, "name": block.name, "input": block.input,
                })
                turn_record["content"].append({"type": "tool_use", "name": block.name, "input": block.input})
                if verbose:
                    print(f"\n[tool_use] {block.name}({json.dumps(block.input)})")

        messages.append({"role": "assistant", "content": assistant_content})
        transcript["turns"].append(turn_record)

        if response.stop_reason != "tool_use":
            break

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            func = TOOL_FUNCTIONS.get(block.name)
            if func is None:
                result = {"error": f"Unknown tool '{block.name}'"}
            else:
                try:
                    result = func(**block.input)
                except Exception as exc:  # surface real tool errors, don't swallow them
                    result = {"error": f"{type(exc).__name__}: {exc}"}

            if verbose:
                print(f"[tool_result] {block.name} -> {json.dumps(result)}")

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
            })

        messages.append({"role": "user", "content": tool_results})
    else:
        transcript["incomplete"] = True
        trace.get_current_span().set_attribute("agent.incomplete", True)
        if verbose:
            print(f"\n[WARNING] Hit max_iterations ({max_iterations}) without a final answer.")

    transcript["final_messages"] = messages
    return transcript


if __name__ == "__main__":
    run_agent("Close out the auction for item A-100 and tell me who won.")
