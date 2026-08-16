"""In-memory mock dataset for the auction-closing agent.

Four items covering the interesting edge cases:
  A-100: normal auction, multiple bids, reserve met
  A-101: no bids at all
  A-102: bids exist, but the highest bid does not meet reserve
  A-103: bid amount exactly equals reserve (boundary case)
"""

ITEMS = {
    "A-100": {
        "name": "Vintage Leica M3 Camera",
        "reserve": 500.00,
        "bids": [
            {"bidder_id": "B-01", "amount": 420.00},
            {"bidder_id": "B-02", "amount": 610.00},
            {"bidder_id": "B-03", "amount": 585.00},
        ],
    },
    "A-101": {
        "name": "Antique Oak Writing Desk",
        "reserve": 300.00,
        "bids": [],
    },
    "A-102": {
        "name": "Signed First-Edition Novel",
        "reserve": 75.00,
        "bids": [
            {"bidder_id": "B-04", "amount": 40.00},
            {"bidder_id": "B-05", "amount": 55.00},
        ],
    },
    "A-103": {
        "name": "Hand-Woven Persian Rug",
        "reserve": 200.00,
        "bids": [
            {"bidder_id": "B-06", "amount": 200.00},
            {"bidder_id": "B-07", "amount": 150.00},
        ],
    },
}
