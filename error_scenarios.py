"""triggers real error conditions in the auction agent, for
testing what error telemetry looks like in Observe. Each scenario overrides
one piece of run_agent's config for a single call

Run all: python error_scenarios.py
Run one: python error_scenarios.py bad_api_key
"""

import sys

from auction_agent import run_agent


def bad_api_key():
    """Invalid credentials -> anthropic.AuthenticationError, uncaught."""
    run_agent(
        "Close out the auction for item A-100 and tell me who won.",
        api_key="sk-ant-invalid-key-00000000000000000000000",
    )


def bad_model():
    """Nonexistent model -> anthropic.NotFoundError, uncaught. Fails fast,
    no tokens billed."""
    run_agent(
        "Close out the auction for item A-100 and tell me who won.",
        model="claude-nonexistent-model-xyz",
    )


def request_timeout():
    """Absurdly short client timeout -> anthropic.APITimeoutError, uncaught.
    Deterministic -- no need to actually kill your network."""
    run_agent(
        "Close out the auction for item A-100 and tell me who won.",
        timeout=0.01,
    )


def exhausted_budget():
    """Caps max_iterations below what the task needs, so the agent runs out
    of budget mid-task instead of reaching a final answer. Not an exception --
    look for transcript['incomplete'] = True and the [WARNING] log line."""
    run_agent(
        "Close out auctions A-100, A-102, and A-103, and give me a summary of each outcome.",
        max_iterations=1,
    )


SCENARIOS = {
    "bad_api_key": bad_api_key,
    "bad_model": bad_model,
    "request_timeout": request_timeout,
    "exhausted_budget": exhausted_budget,
}


if __name__ == "__main__":
    requested = sys.argv[1:] or list(SCENARIOS.keys())

    for name in requested:
        if name not in SCENARIOS:
            print(f"Unknown scenario '{name}'. Options: {', '.join(SCENARIOS)}")
            continue

        print(f"\n{'#' * 80}\nSCENARIO: {name}\n{'#' * 80}")
        try:
            SCENARIOS[name]()
        except Exception as exc:
            print(f"\n[EXPECTED ERROR] {type(exc).__name__}: {exc}")
