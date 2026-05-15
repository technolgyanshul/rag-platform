#!/usr/bin/env python3
"""Fetch and group open SonarCloud issues for a project.

Usage:
  SONAR_TOKEN=... python scripts/sonar_issues.py \\
    --organization my-org --project-key my-org_rag-platform
"""

from __future__ import annotations

import argparse
import base64
import collections
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_HOST = "https://sonarcloud.io"
PAGE_SIZE = 500


def base64_token(token: str) -> str:
    return base64.b64encode(f"{token}:".encode("utf-8")).decode("ascii")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch open SonarCloud issues grouped by severity/rule/file")
    parser.add_argument("--organization", required=True, help="SonarCloud organization key")
    parser.add_argument("--project-key", required=True, help="SonarCloud project key")
    parser.add_argument("--host-url", default=os.getenv("SONAR_HOST_URL", DEFAULT_HOST), help="Sonar host URL")
    parser.add_argument("--branch", default=None, help="Optional branch name filter")
    parser.add_argument(
        "--pull-request",
        default=None,
        help="Optional PR number to scope pull request analysis issues",
    )
    parser.add_argument(
        "--severities",
        default="BLOCKER,CRITICAL,MAJOR,MINOR,INFO",
        help="Comma-separated severity filters",
    )
    parser.add_argument("--max", type=int, default=200, help="Max issues to display")
    return parser.parse_args()


def fetch_issues(args: argparse.Namespace, token: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    page = 1

    while True:
        params: dict[str, Any] = {
            "organization": args.organization,
            "projects": args.project_key,
            "resolved": "false",
            "ps": PAGE_SIZE,
            "p": page,
            "severities": args.severities,
        }
        if args.branch:
            params["branch"] = args.branch
        if args.pull_request:
            params["pullRequest"] = args.pull_request

        query = urllib.parse.urlencode(params)
        request = urllib.request.Request(
            f"{args.host_url.rstrip('/')}/api/issues/search?{query}",
            headers={
                "Authorization": f"Basic {base64_token(token)}",
                "Accept": "application/json",
            },
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
        batch = payload.get("issues", [])
        if not batch:
            break

        issues.extend(batch)
        total = int(payload.get("total", 0))
        if len(issues) >= total:
            break
        page += 1

    return issues


def group_issues(issues: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = collections.defaultdict(lambda: collections.defaultdict(list))

    for issue in issues:
        severity = issue.get("severity", "UNKNOWN")
        rule = issue.get("rule", "unknown-rule")
        component = issue.get("component", "unknown-component")
        grouped[severity][rule].append(
            {
                "key": issue.get("key"),
                "message": issue.get("message"),
                "component": component,
                "line": issue.get("line"),
                "status": issue.get("status"),
                "effort": issue.get("effort"),
            }
        )

    return grouped


def print_grouped(grouped: dict[str, Any], max_issues: int) -> None:
    ordered_severity = ["BLOCKER", "CRITICAL", "MAJOR", "MINOR", "INFO", "UNKNOWN"]
    emitted = 0

    for severity in ordered_severity:
        if severity not in grouped:
            continue
        print(f"\n## {severity}")
        rules = grouped[severity]
        for rule in sorted(rules.keys()):
            entries = sorted(
                rules[rule],
                key=lambda row: (str(row.get("component", "")), int(row.get("line") or 0)),
            )
            print(f"- Rule: {rule} ({len(entries)} issues)")
            for row in entries:
                if emitted >= max_issues:
                    print("  - ...truncated by --max")
                    return
                loc = row["component"]
                if row.get("line"):
                    loc = f"{loc}:{row['line']}"
                print(f"  - {loc} | {row['message']} | key={row['key']}")
                emitted += 1


def main() -> int:
    args = parse_args()
    token = os.getenv("SONAR_TOKEN")
    if not token:
        print("SONAR_TOKEN is required in environment", file=sys.stderr)
        return 2

    try:
        issues = fetch_issues(args, token)
    except urllib.error.HTTPError as exc:
        print(f"Sonar API request failed: {exc}", file=sys.stderr)
        body = exc.read().decode("utf-8", errors="replace")
        if body:
            print(body, file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Sonar API request failed: {exc}", file=sys.stderr)
        return 1

    grouped = group_issues(issues)
    print(f"Total open issues fetched: {len(issues)}")
    print_grouped(grouped, args.max)

    print("\nJSON summary:")
    print(json.dumps({"total": len(issues), "grouped": grouped}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
