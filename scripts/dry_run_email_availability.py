import argparse
import os
import sys
from datetime import datetime


def _parse_date(s: str) -> datetime:
    # Interpret as YYYY-MM-DD; timezone windowing is handled in the app code (PST).
    return datetime.strptime(s, "%Y-%m-%d")


def main() -> int:
    # Ensure `app` package is importable when run as a script.
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    parser = argparse.ArgumentParser(
        description="Dry run: probe Gmail for newsletter emails (no OpenAI/video)."
    )
    parser.add_argument(
        "--date",
        help="Optional PST date to check (YYYY-MM-DD). If omitted, checks last 24 hours.",
        default=None,
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=3,
        help="Max sample emails per source (1-20).",
    )
    args = parser.parse_args()

    target_date = _parse_date(args.date) if args.date else None

    from app.core.agents.ai_news_summarizer import probe_email_availability

    report = probe_email_availability(target_date=target_date, max_results=args.max_results)
    total = sum(item.get("count", 0) for item in report)

    print(f"total_found={total}")
    for item in report:
        print(f"- source={item['source']} window={item['window']} count={item['count']}")
        print(f"  query={item['query']}")
        if item.get("error"):
            print(f"  error={item['error']}")
        for s in item.get("samples", []):
            print(f"  - subject={s.get('subject')!r} date={s.get('date')!r} body_len={s.get('body_len')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

