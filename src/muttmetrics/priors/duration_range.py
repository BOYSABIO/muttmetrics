"""CLI: duration range for a dog (#26).

Usage:
  python -m muttmetrics.priors --dog-id 1 [--as-of 2026-10-06] [--service-id 4]
  python -m muttmetrics.priors.duration_range --dog-id 1 …
"""

from __future__ import annotations

import argparse
import json
from datetime import date

from muttmetrics.api.services.visit_predictions import score_dog_duration_range
from muttmetrics.db.session import session_scope


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="P50/P90 duration range for a dog")
    parser.add_argument("--dog-id", type=int, required=True)
    parser.add_argument("--as-of", type=date.fromisoformat, default=None)
    parser.add_argument("--service-id", type=int, default=None)
    args = parser.parse_args(argv)

    as_of = args.as_of or date.today()
    with session_scope() as session:
        try:
            result = score_dog_duration_range(
                session,
                dog_id=args.dog_id,
                as_of=as_of,
                service_id=args.service_id,
            )
        except LookupError as exc:
            print(exc)
            return 1

    print(
        json.dumps(
            {
                "dog_id": result.dog_id,
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
