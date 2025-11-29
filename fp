#!/bin/bash
# Financial Planner wrapper script
# Usage: ./fp [arguments]
# Example: ./fp myprogram --mode TaxDetails

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python "$SCRIPT_DIR/src/Program.py" "$@"
