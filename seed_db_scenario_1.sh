#!/bin/bash
# Seeds scenario 1: 3 observatories with increasing complexity (10 / 100 / 1000 products).
# Requires the API server to be running (default: http://localhost:5000).
#
# Usage:
#   ./seed_db_scenario_1.sh [--api-url URL] [--username USER] [--password PASS] [--clean] [--clean-only]
#
# Examples:
#   ./seed_db_scenario_1.sh
#   ./seed_db_scenario_1.sh --clean
#   ./seed_db_scenario_1.sh --api-url http://localhost:5000 --username admin --password secret
python3 ./examples/seed_scenario_1.py "$@"
