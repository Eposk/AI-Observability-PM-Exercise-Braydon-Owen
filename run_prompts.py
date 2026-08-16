"""Covers: happy path, no bids, reserve not met, reserve exactly met,
direct invoice request (skipping discovery), an ambiguous item
reference, a non-existent item, an incorrect premise,
a question outside the scope of the agent, and a multi-stepped request
"""

from auction_agent import run_agent

PROMPTS = [
    "Close out the auction for item A-100 and tell me who won.",
    "Item A-101 got no bids, what do we do?",
    "The bid on item A-102 was $40 but the reserve was $75 -- what happens?",
    "Close out the auction for item A-103 and tell me the final invoice.",
    "Generate the invoice for item A-100 directly.",
    "What's the status of the Henderson auction?",
    "Close out auction A-999.",
    "Item A-101 was sold. show me who won",
    "Find me items that were bid on but didn't meet the reserve price",
    "Close out auctions A-100, A-102, and A-103, and give me a summary of each outcome.",
]

if __name__ == "__main__":
    for prompt in PROMPTS:
        run_agent(prompt)
        print("\n")
