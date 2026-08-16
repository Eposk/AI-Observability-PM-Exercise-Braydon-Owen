#!/bin/bash
cd "$(dirname "$0")"

echo "Auction Agent -- Run All Prompts"
echo "================================="
echo ""

if [ ! -d venv ]; then
    echo "First run: setting up environment (installs a few packages, ~1 min)..."
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip -q
    ./venv/bin/pip install -r requirements.txt -q
    echo "Setup complete."
    echo ""
fi

if [ ! -f .env ] || ! grep -q "ANTHROPIC_API_KEY=.\+" .env 2>/dev/null; then
    echo "No Anthropic API key found."
    echo ""
    echo "Create a file named .env in this same folder containing:"
    echo "  ANTHROPIC_API_KEY=your-key-here"
    echo ""
    echo "(see .env.example for the template)"
    echo ""
    read -p "Press Enter to close..."
    exit 1
fi

echo "Running all test prompts against the auction-closing agent..."
echo ""
./venv/bin/python run_prompts.py

echo ""
echo "================================="
echo "Done."
read -p "Press Enter to close..."
