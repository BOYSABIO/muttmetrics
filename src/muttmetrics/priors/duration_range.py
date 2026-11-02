"""CLI: duration range for a pet (#26).

Usage:
  python -m muttmetrics.priors --pet-id 1 [--as-of 2026-10-06] [--service-id 4]
  python -m muttmetrics.priors.duration_range --pet-id 1 …
"""

from __future__ import annotations

import argparse
import json
from datetime import date

from muttmetrics.db.session import session_scope
from muttmetrics.services.visit_predictions import score_pet_duration_range


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="P50/P90 duration range for a pet")
    parser.add_argument("--pet-id", type=int, required=True)
    parser.add_argument("--as-of", type=date.fromisoformat, default=None)
    parser.add_argument("--service-id", type=int, default=None)
    args = parser.parse_args(argv)

    as_of = args.as_of or date.today()
    with session_scope() as session:
        try:
            result = score_pet_duration_range(
                session,
                pet_id=args.pet_id,
                as_of=as_of,
                service_id=args.service_id,
            )
        except LookupError as exc:
            print(exc)
            return 1

    print(
        json.dumps(
            {
                "pet_id": result.pet_id,
                "service_id": result.service_id,
                "as_of": result.as_of.isoformat(),
                "days_since_last": result.days_since_last,
                "predicted_min_p50": result.predicted_min_p50,
                "predicted_min_p90": result.predicted_min_p90,
                "skipped_reason": result.skipped_reason,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
