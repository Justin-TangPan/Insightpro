"""Command-line maintenance entry points used by the external health guard."""
import argparse
import json


def repair_freshness() -> int:
    from services.startup_service import run_startup_catchup
    from services.system_health_service import get_readiness_report

    run_startup_catchup()
    report = get_readiness_report()
    print(json.dumps(report, ensure_ascii=False, default=str))
    return 0 if report.get("status") == "healthy" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="InsightPro maintenance commands")
    parser.add_argument("command", choices=["repair-freshness"])
    args = parser.parse_args()
    if args.command == "repair-freshness":
        return repair_freshness()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
