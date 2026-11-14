"""CLI entry: python -m muttmetrics.seed [--breeds-only]

Plain run: services, add-ons and breeds (a fresh dev or CI database).
--breeds-only: just the breed catalog. Use this on the server: the full run
also rewrites services, and without data/private/pricing.json it would set
every service's price_base to NULL.
"""

import argparse

from muttmetrics.seed.run import seed_breeds, seed_reference_data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--breeds-only",
        action="store_true",
        help="upsert only the breed catalog (safe on the server)",
    )
    args = parser.parse_args()
    if args.breeds_only:
        seed_breeds()
    else:
        seed_reference_data()


if __name__ == "__main__":
    main()
