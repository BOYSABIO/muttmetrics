"""CLI entry: python -m muttmetrics.seed"""

from muttmetrics.seed.run import seed_reference_data


def main() -> None:
    seed_reference_data()


if __name__ == "__main__":
    main()
