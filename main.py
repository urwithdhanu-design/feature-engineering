"""CLI entry point for the credit card nudge recommendation platform."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"


def _write_summary(out_path: Path, account: dict, result: dict) -> None:
    reward = result.get("reward_eligibility", {})
    risk = result.get("payment_risk", {})
    segment = result.get("customer_segment") or {}
    seg_name = segment.get("name", "n/a") if isinstance(segment, dict) else segment
    seg_label = segment.get("label", "") if isinstance(segment, dict) else ""
    lines = [
        f"Customer ID     : {result.get('customerId', account.get('customerId'))}",
        f"Payment history : {result.get('payment_history_string', '')}",
        f"Customer segment: {seg_name} (id={segment.get('id', 'n/a')})" if isinstance(segment, dict) else f"Customer segment: {seg_name}",
    ]
    if seg_label:
        lines.append(f"Segment meaning : {seg_label}")
    if isinstance(segment, dict) and segment.get("n_clusters"):
        lines.append(f"Clusters trained: {segment['n_clusters']} behavioural groups (not age personas)")
    lines.extend([
        f"Nudge type      : {result.get('nudge_type')}",
        f"Tone            : {result.get('tone')}",
        f"Show in UI      : {result.get('show_nudge')}",
        "",
        "Message:",
        result.get("message", ""),
        "",
        "Payment risk:",
        f"  Missed payment    : {risk.get('risk_missed_payment', 0):.1%}",
        f"  Late payment      : {risk.get('risk_late_payment', 0):.1%}",
        f"  Minimum only      : {risk.get('risk_minimum_only_payment', 0):.1%}",
        "",
        "£20 reward:",
        f"  Eligible          : {reward.get('eligible')}",
        f"  On-time payments  : {reward.get('on_time_payments_count')}",
        f"  Still needed      : {reward.get('payments_needed')}",
    ])
    if reward.get("blockers"):
        lines.append(f"  Blockers          : {', '.join(reward['blockers'])}")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_run(args: argparse.Namespace) -> None:
    from src.inference.recommender import recommend_for_account

    input_dir = Path(args.input_dir) if args.input_dir else INPUT_DIR
    output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR

    if not input_dir.exists():
        print(f"Input folder not found: {input_dir}", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    model_path = ROOT / "models" / "model_bundle.pkl"
    if not model_path.exists():
        print("Model not found. Run first: python main.py train", file=sys.stderr)
        sys.exit(1)

    json_files = sorted(input_dir.glob("*.json"))
    if not json_files:
        print(f"No JSON files in {input_dir}", file=sys.stderr)
        sys.exit(1)

    processed = 0
    for in_path in json_files:
        account = json.loads(in_path.read_text(encoding="utf-8"))
        result = recommend_for_account(account)

        stem = in_path.stem
        rec_path = output_dir / f"{stem}_recommendation.json"
        sum_path = output_dir / f"{stem}_summary.txt"

        rec_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        _write_summary(sum_path, account, result)
        processed += 1
        print(f"OK  {in_path.name}  ->  {rec_path.name}, {sum_path.name}")

    print(f"\nProcessed {processed} customer(s). Output folder: {output_dir}")


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
    metrics = train_and_save(dataset_path=dataset, n_clusters=args.clusters)
    print(json.dumps(metrics, indent=2))


def cmd_recommend_random(args: argparse.Namespace) -> None:
    import random

    from scripts.generate_synthetic_training_data import build_synthetic_customer
    from src.inference.recommender import recommend_for_account

    if args.from_training:
        training_file = ROOT / "data" / "training" / "synthetic_5000_2mo.jsonl"
        if not training_file.exists():
            print("Training file not found. Run: python main.py generate-synthetic", file=sys.stderr)
            sys.exit(1)
        lines = [ln for ln in training_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        account = json.loads(random.choice(lines))
        source = "training dataset"
    else:
        rng = random.Random()
        account = build_synthetic_customer(
            index=random.randint(10000, 99999),
            rng=rng,
            history_months=args.months,
        )
        source = "newly generated random customer"

    print(f"--- Input ({source}) ---", file=sys.stderr)
    print(json.dumps(account, indent=2), file=sys.stderr)
    print("--- Recommendation ---", file=sys.stderr)
    result = recommend_for_account(account)
    print(json.dumps(result, indent=2))


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
    train.add_argument(
        "--clusters",
        type=int,
        default=3,
        help="Number of K-Means customer segments (default: 3)",
    )
    train.set_defaults(func=cmd_train)

    run = sub.add_parser(
        "run",
        help="Process all JSON files in input/ and write results to output/",
    )
    run.add_argument("--input-dir", help=f"Input folder (default: {INPUT_DIR.name}/)")
    run.add_argument("--output-dir", help=f"Output folder (default: {OUTPUT_DIR.name}/)")
    run.set_defaults(func=cmd_run)

    rec = sub.add_parser("recommend", help="Get nudge recommendation for an account JSON")
    rec.add_argument("account_file", help="Path to account JSON file")
    rec.set_defaults(func=cmd_recommend)

    rnd = sub.add_parser("recommend-random", help="Test with a random synthetic customer")
    rnd.add_argument(
        "--from-training",
        action="store_true",
        help="Pick a random customer from synthetic_5000_2mo.jsonl",
    )
    rnd.add_argument("--months", type=int, default=2, help="History months if generating fresh")
    rnd.set_defaults(func=cmd_recommend_random)

    demo = sub.add_parser("demo", help="Demo recommendation for a persona scenario")
    demo.add_argument("--persona", choices=["ethan", "sarah", "jordan"], default="ethan")
    demo.add_argument("--scenario", default="MMM", help="Payment history code e.g. MMM, XXL")
    demo.set_defaults(func=cmd_demo)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
