#!/bin/bash
set -e

echo "=== Running Tests ==="
for f in tests/test_*.py; do python3 "$f" > /dev/null; done
echo "All tests passed (zero regressions)."

echo -e "\n=== Demo Sequence ==="
echo ">>> nova reset (confirm y)"
echo "y" | python3 -m packages.cli.main reset 2>&1 | grep -v 'runpy' || true

echo -e "\n>>> nova ingest plaintext 'Decision: Deploy the new web platform'"
OUT1=$(python3 -m packages.cli.main ingest plaintext "Decision: Deploy the new web platform" 2>&1 | grep -v 'runpy')
echo "$OUT1"
FACT1=$(echo "$OUT1" | awk '/kir_obs/ {print $NF}')

echo -e "\n>>> nova ingest plaintext 'Assumption: Deployment will take 5 hours'"
OUT2=$(python3 -m packages.cli.main ingest plaintext "Assumption: Deployment will take 5 hours" 2>&1 | grep -v 'runpy')
echo "$OUT2"
FACT2=$(echo "$OUT2" | awk '/kir_obs/ {print $NF}')

echo -e "\n>>> nova ingest plaintext 'Risk: Deployment may cause downtime'"
OUT3=$(python3 -m packages.cli.main ingest plaintext "Risk: Deployment may cause downtime" 2>&1 | grep -v 'runpy')
echo "$OUT3"
FACT3=$(echo "$OUT3" | awk '/kir_obs/ {print $NF}')

echo -e "\n>>> nova log"
python3 -m packages.cli.main log 2>&1 | grep -v 'runpy'

echo -e "\n>>> nova explain $FACT2"
python3 -m packages.cli.main explain "$FACT2" 2>&1 | grep -v 'runpy'

echo -e "\n>>> nova explain $FACT3"
python3 -m packages.cli.main explain "$FACT3" 2>&1 | grep -v 'runpy'
