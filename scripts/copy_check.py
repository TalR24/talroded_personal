#!/usr/bin/env python3
"""
copy_check.py — keep the public copy about Tal in step with profile_facts.json.

Layer 2 of the copy-currency system (Sep 3 2026). What it does:

  1. Refreshes live NUMBERS (fiscal records, obligations, laws, State Capacity
     orgs) from their sources and rewrites every embedded number listed in
     profile_facts.json -> embedded_numbers, using each fact's display rule.
     These are mechanical and safe to commit unattended.
  2. Runs scripts/sync_posts.py and reconciles the two post counts. Substack
     blocks GitHub Actions IPs, so in --ci mode this step is skipped and
     reported as "run locally".
  3. Scans every personal-site page (and, when reachable, the data site and
     State Capacity About pages, the Substack subscribe page and homepage
     links) for BANNED strings, stale descriptors, and em dashes in prose.
     These need a human, so they are reported, never auto-fixed.
  4. Writes copy_reports/copy_check_YYYY-MM-DD.md and prints a summary.
     Exit 0 always in --ci (the workflow reads the report and opens an issue
     if there are flags); exit 1 with --strict when there are flags.

Usage:
    python3 scripts/copy_check.py            # full, local (Substack reachable)
    python3 scripts/copy_check.py --ci       # GitHub Actions: skips Substack
    python3 scripts/copy_check.py --strict   # exit 1 on any prose flag
    python3 scripts/copy_check.py --no-write # report only, touch nothing
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / "profile_facts.json"
REPORTS = ROOT / "copy_reports"
UA = {"User-Agent": "Mozilla/5.0 (compatible; copy-check/1.0; +https://talroded.nycuriosity.com)"}


def fmt(value: int, rule: str) -> str:
    if rule == "exact":
        return f"{value:,}" if value >= 10000 else str(value)
    if rule == "floor10plus":
        return f"{value // 10 * 10}+"
    if rule == "floor100plus":
        return f"{value // 100 * 100:,}+"
    if rule == "floor1000plus":
        return f"{value // 1000 * 1000:,}+"
    return str(value)


def get_json(url: str):
    r = requests.get(url, headers=UA, timeout=60)
    r.raise_for_status()
    return r.json()


def dig(obj, path: str):
    for part in path.split("."):
        if part == "length":
            return len(obj)
        obj = obj[part]
    return obj


def refresh_numbers(facts: dict, log: list[str]) -> dict[str, int]:
    """Fetch every live-sourced number. Returns {fact: value} for the ones that resolved."""
    live: dict[str, int] = {}
    for key, spec in facts["numbers"].items():
        if key.startswith("_"):
            continue
        src = spec.get("source", "")
        try:
            if src.startswith("http") and src.endswith(".json"):
                live[key] = int(dig(get_json(src), spec["path"]))
            elif src.startswith("http") and src.endswith(".csv"):
                r = requests.get(src, headers=UA, timeout=60)
                r.raise_for_status()
                rows = [row for row in csv.DictReader(io.StringIO(r.text)) if any(v.strip() for v in row.values())]
                live[key] = len(rows)
            elif src in ("writing_page", "substack_archive"):
                continue  # both come from count_archive()
            else:
                continue
        except Exception as e:  # noqa: BLE001
            log.append(f"- could not fetch `{key}` from {src}: {e}")
    return live


def sync_posts(ci: bool, log: list[str]) -> None:
    """Run sync_posts.py to pull any new Substack posts into writing/index.html.
    Substack blocks GitHub Actions IPs, so this is skipped in --ci. The post
    COUNT is never read from Substack's API: the anonymous archive endpoint
    returns only ~23 recent posts (Sep 2026), so counts come from the
    writing page instead (see count_archive)."""
    if ci:
        log.append("- Substack post sync skipped in CI (Substack blocks GitHub Actions IPs). Run `python3 scripts/copy_check.py` locally at the sweep.")
        return
    try:
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "sync_posts.py")], capture_output=True, text=True, timeout=300)
        added = len(re.findall(r"\+ New post:", out.stdout))
        log.append(f"- sync_posts.py added {added} new post(s) to writing/index.html" if added else "- sync_posts.py: no new posts")
    except Exception as e:  # noqa: BLE001
        log.append(f"- post sync failed: {e}")


def count_archive() -> tuple[int, int]:
    """(rows in #archive, rows that are NYCuriosity posts). Cross-posts are
    <div class="archive-item"> rows whose title links Substack; external rows
    (Reboot Democracy) carry no nycuriosity.com link. The Visualize Curiosity
    list below the marker is a separate .archive-list and is excluded."""
    html = (ROOT / "writing" / "index.html").read_text(encoding="utf-8")
    i = html.index('<div class="archive-list" id="archive">')
    j = html.find('<div class="archive-list"', i + 10)
    block = html[i:(j if j > 0 else len(html))]
    chunks = block.split('class="archive-item"')[1:]
    posts = sum(1 for c in chunks if "nycuriosity.com/p/" in c)
    return len(chunks), posts


def apply_numbers(facts: dict, live: dict[str, int], write: bool, log: list[str]) -> list[str]:
    """Rewrite embedded numbers whose fact changed. Returns list of changed files."""
    changed: set[str] = set()
    for item in facts["embedded_numbers"]:
        key = item["fact"]
        if key not in live:
            continue
        spec = facts["numbers"][key]
        want = fmt(live[key], spec.get("display", "exact"))
        path = ROOT / item["file"]
        html = path.read_text(encoding="utf-8")
        m = re.search(item["regex"], html)
        if not m:
            log.append(f"- pattern not found in {item['file']}: `{item['regex']}`")
            continue
        if m.group(1) != want:
            new = html[:m.start(1)] + want + html[m.end(1):]
            log.append(f"- {item['file']}: `{m.group(1)}` -> `{want}` ({key})")
            if write:
                path.write_text(new, encoding="utf-8")
            changed.add(item["file"])
    return sorted(changed)


def strip_head_and_tags(html: str) -> str:
    html = re.sub(r"<head[\s\S]*?</head>", "", html, flags=re.I)
    html = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", "", html, flags=re.I)
    return html


def scan_banned(facts: dict, log: list[str]) -> list[str]:
    flags: list[str] = []
    for rel in facts["surfaces"]["personal_site"]["files"]:
        path = ROOT / rel
        if not path.exists():
            continue
        raw = path.read_text(encoding="utf-8")
        body = strip_head_and_tags(raw)
        for b in facts["banned_strings"]:
            if rel in b.get("allow_files", []):
                continue
            hay = body if b.get("prose_only") else raw
            if b["text"] in hay:
                n = hay.count(b["text"])
                flags.append(f"{rel}: contains {b['text'].strip()!r} x{n} ({b['why']})")
    # descriptor must appear verbatim where it is supposed to
    desc = facts["descriptor"]["nycuriosity"]
    for rel in ("index.html", "resume/index.html", "writing/index.html"):
        raw = (ROOT / rel).read_text(encoding="utf-8")
        if desc not in raw and desc[0].upper() + desc[1:] not in raw:
            flags.append(f"{rel}: canonical NYCuriosity descriptor not found verbatim")
    return flags


def scan_remote(facts: dict, ci: bool, log: list[str]) -> list[str]:
    flags: list[str] = []
    for name, spec in facts["surfaces"].items():
        if name.startswith("_") or "url" not in spec:
            continue
        if ci and not spec.get("ci", True):
            log.append(f"- {name}: skipped in CI (Substack)")
            continue
        try:
            r = requests.get(spec["url"], headers=UA, timeout=60)
            if r.status_code != 200:
                log.append(f"- {name}: HTTP {r.status_code}")
                continue
            body = strip_head_and_tags(r.text)
            for b in facts["banned_strings"]:
                if b.get("prose_only"):
                    continue
                if b["text"] in body:
                    flags.append(f"{name} ({spec['url']}): contains {b['text']!r}")
            if name == "substack_hero" and facts["descriptor"]["substack_hero_text"] not in body:
                flags.append("substack_hero: live subscribe page does not show the canonical hero text")
        except Exception as e:  # noqa: BLE001
            log.append(f"- {name}: fetch failed: {e}")
    return flags


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ci", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()
    write = not args.no_write

    facts = json.loads(FACTS.read_text(encoding="utf-8"))
    log: list[str] = []

    sync_posts(args.ci, log)
    live = refresh_numbers(facts, log)
    live["archive_rows"], live["posts"] = count_archive()

    changed = apply_numbers(facts, live, write, log)

    # persist observed values into the facts file so the next diff is against today's truth
    if write:
        for k, v in live.items():
            facts["numbers"][k]["value"] = v
        facts["numbers_observed"] = date.today().isoformat()
        FACTS.write_text(json.dumps(facts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    flags = scan_banned(facts, log) + scan_remote(facts, args.ci, log)

    lines = [f"# Copy check — {date.today().isoformat()}" + (" (CI)" if args.ci else " (local)"), ""]
    lines += ["## Live numbers", ""] + [f"- {k}: {v}" for k, v in sorted(live.items())] + [""]
    lines += ["## Numbers rewritten in copy", ""] + ([f"- {c}" for c in changed] or ["- none"]) + [""]
    lines += ["## Needs a human", ""] + ([f"- {f}" for f in flags] or ["- nothing flagged"]) + [""]
    lines += ["## Log", ""] + (log or ["- clean"]) + [""]
    report = "\n".join(lines)
    print(report)
    if write:
        REPORTS.mkdir(exist_ok=True)
        (REPORTS / f"copy_check_{date.today().isoformat()}.md").write_text(report, encoding="utf-8")
        (REPORTS / "latest.md").write_text(report, encoding="utf-8")
    if args.strict and flags:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
