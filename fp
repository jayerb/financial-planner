#!/bin/bash
# Financial Planner Command-Line Interface
# Usage: ./fp [plan_name]
# Example: ./fp myprograms

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python "$SCRIPT_DIR/src/shell.py" "$@"
