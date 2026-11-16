#!/usr/bin/env bash
# Pick which pipeline to set up:
#   2.0  poc/          the original POC (one product photo per call; temples can come out wrong)
#   2.1  ar-imac2.1/   temple-locked: front + three-quarter + temple product views, temple gate
#
# bash install.sh          asks
# bash install.sh 2.1      no prompt
set -euo pipefail
cd "$(dirname "$0")"

VERSION="${1:-}"
if [ -z "$VERSION" ]; then
  echo "Which version do you want to install?"
  echo "  1) AR-iMac 2.1  temple-locked (recommended)"
  echo "  2) v2.0 POC     original scripts in poc/"
  read -r -p "Choose 1 or 2 [1]: " pick
  case "${pick:-1}" in 1) VERSION=2.1 ;; 2) VERSION=2.0 ;; *) echo "unknown choice: $pick"; exit 1 ;; esac
fi

case "$VERSION" in
  2.1) DIR=ar-imac2.1; REQ=ar-imac2.1/requirements.txt; MODELS=ar-imac2.1/get_models.sh ;;
  2.0) DIR=poc;        REQ=requirements.txt;            MODELS=poc/scripts/get_models.sh ;;
  *) echo "unknown version: $VERSION (use 2.0 or 2.1)"; exit 1 ;;
esac

[ -d .venv ] || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r "$REQ"
bash "$MODELS"
[ -f .env ] || echo "Next: put your fal.ai key in .env as FAL_KEY=..."
echo "Installed $VERSION ($DIR). Activate with: source .venv/bin/activate"
[ "$VERSION" = 2.1 ] && echo "Start with: python3 ar-imac2.1/scripts/pid_refs.py <pid>" || echo "See README.md, section Running the recommended pipeline (v2.0)"
