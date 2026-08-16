"""Interactive REPL for the auction agent. Type a prompt, see the trace/response.

Each turn is a fresh, independent agent run (no shared conversation history
across turns) -- matches how run_prompts.py generates load, just interactive.
Type 'exit' or 'quit' to stop.
"""

from auction_agent import run_agent

if __name__ == "__main__":
    print("Auction agent REPL. Type a prompt (or 'exit' to quit).\n")
    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            break

        run_agent(user_input)
        print()
