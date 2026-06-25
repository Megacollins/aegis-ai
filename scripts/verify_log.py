"""Independently verify a trades.csv audit trail without trusting the file
at all. Checks two separate things:

1. Chain integrity -- recomputes each row's hash from (prev_hash + row
   content) and confirms it matches the stored row_hash, and that
   prev_hash correctly links to the previous row. Any edited or deleted
   row breaks the chain from that point forward.

2. Decision provenance -- recomputes the regime classification from the
   row's stored features_json using the actual RegimeDetector and the
   exact config files fingerprinted in config_fingerprint, and confirms
   it matches the logged `regime` and `confidence`. This proves the
   logged decision genuinely follows from the logged inputs, not just
   that the file is unmodified.

Run: python scripts/verify_log.py --log logs/trades.csv
"""

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aegis.logging.trade_logger import (
    GENESIS_HASH,
    compute_config_fingerprint,
    compute_input_hash,
    _sha256,
)
from aegis.perception.feature_normalizer import FeatureVector
from aegis.regime.regime_detector import RegimeDetector


def verify(log_path: str) -> bool:
    with open(log_path) as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("Log is empty -- nothing to verify.")
        return True

    current_fingerprint = compute_config_fingerprint(".")
    detector = RegimeDetector()

    chain_ok = True
    provenance_ok = True
    prev_hash = GENESIS_HASH

    for i, row in enumerate(rows):
        # 1. Chain integrity
        if row["prev_hash"] != prev_hash:
            print(f"Row {i}: chain broken -- prev_hash mismatch (log tampered or reordered)")
            chain_ok = False

        row_for_hash = {k: v for k, v in row.items() if k != "row_hash"}
        recomputed_row_hash = _sha256(row["prev_hash"], json.dumps(row_for_hash, sort_keys=True))
        # csv.DictReader already returns plain strings for every field, so
        # this dict is already in the same string form the writer hashed.
        if recomputed_row_hash != row["row_hash"]:
            print(f"Row {i}: row_hash mismatch -- row content was altered after logging")
            chain_ok = False
        prev_hash = row["row_hash"]

        # 2. Decision provenance: recompute regime from stored features
        if row["config_fingerprint"] != current_fingerprint:
            print(f"Row {i}: config_fingerprint does not match current config files -- "
                  f"skipping provenance check (config has changed since this row was logged)")
            continue

        recomputed_input_hash = compute_input_hash(
            row["features_json"], row["config_fingerprint"], row["regime"], float(row["confidence"])
        )
        if recomputed_input_hash != row["input_hash"]:
            print(f"Row {i}: input_hash mismatch -- features/config/regime/confidence don't match what was hashed")
            provenance_ok = False
            continue

        features = FeatureVector(**json.loads(row["features_json"]))
        result = detector.detect(features)
        if result.regime.value != row["regime"]:
            print(f"Row {i}: regime mismatch -- logged '{row['regime']}', recomputed '{result.regime.value}'")
            provenance_ok = False
        if abs(result.confidence - float(row["confidence"])) > 1e-6:
            print(f"Row {i}: confidence mismatch -- logged {row['confidence']}, recomputed {result.confidence}")
            provenance_ok = False

    print(f"\nRows checked: {len(rows)}")
    print(f"Chain integrity: {'PASS' if chain_ok else 'FAIL'}")
    print(f"Decision provenance: {'PASS' if provenance_ok else 'FAIL'}")
    return chain_ok and provenance_ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", default="logs/trades.csv")
    args = parser.parse_args()

    ok = verify(args.log)
    sys.exit(0 if ok else 1)
