"""CLI entry point for the credit card nudge recommendation platform."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def cmd_generate(_: argparse.Namespace) -> None:
    from scripts.generate_scenarios import generate_all
    count = generate_all()
    print(f"Generated {count} scenario JSON files.")


def cmd_generate_synthetic(args: argparse.Namespace) -> None:
    from scripts.generate_synthetic_training_data import generate_dataset
    path = generate_dataset(
        count=args.count,
        history_months=args.months,
        seed=args.seed,
    )
    print(f"Generated {args.count} synthetic customers ({args.months} months each).")
    print(f"Output: {path}")


def cmd_train(args: argparse.Namespace) -> None:
    from pathlib import Path

    from src.models.train import train_and_save

    dataset = Path(args.dataset) if args.dataset else None
    metrics = train_and_save(dataset_path=dataset)
    print(json.dumps(metrics, indent=2))


def cmd_recommend(args: argparse.Namespace) -> None:
    from src.inference.recommender import recommend_for_account
    path = Path(args.account_file)
    account = json.loads(path.read_text(encoding="utf-8"))
    result = recommend_for_account(account)
    print(json.dumps(result, indent=2))


def cmd_demo(args: argparse.Namespace) -> None:
    from src.inference.recommender import recommend_for_account
    persona = args.persona or "ethan"
    scenario = args.scenario or "MMM"
    path = ROOT / "data" / "scenarios" / persona / f"{scenario}.json"
    if not path.exists():
        print(f"Scenario not found: {path}", file=sys.stderr)
        sys.exit(1)
    account = json.loads(path.read_text(encoding="utf-8"))
    result = recommend_for_account(account)
    print(json.dumps(result, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Credit card missing payments — nudge & risk ML platform"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate all persona scenario JSON files")
    gen.set_defaults(func=cmd_generate)

    syn = sub.add_parser(
        "generate-synthetic",
        help="Generate large synthetic training set (default 5000 customers, 2 months each)",
    )
    syn.add_argument("--count", type=int, default=5000, help="Number of synthetic customers")
    syn.add_argument("--months", type=int, default=2, help="Months of payment history per customer")
    syn.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    syn.set_defaults(func=cmd_generate_synthetic)

    train = sub.add_parser("train", help="Train ML models on training data")
    train.add_argument(
        "--dataset",
        help="Path to JSONL training file (default: data/training/synthetic_5000_2mo.jsonl if present)",
    )
    train.set_defaults(func=cmd_train)

    rec = sub.add_parser("recommend", help="Get nudge recommendation for an account JSON")
    rec.add_argument("account_file", help="Path to account JSON file")
    rec.set_defaults(func=cmd_recommend)

    demo = sub.add_parser("demo", help="Demo recommendation for a persona scenario")
    demo.add_argument("--persona", choices=["ethan", "sarah", "jordan"], default="ethan")
    demo.add_argument("--scenario", default="MMM", help="Payment history code e.g. MMM, XXL")
    demo.set_defaults(func=cmd_demo)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
