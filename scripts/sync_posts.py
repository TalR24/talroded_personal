"""
sync_posts.py
Fetches the NYCuriosity Substack RSS feed and inserts any posts
not already listed into writing/index.html (newest first).

Run locally:  python scripts/sync_posts.py
Run via CI:   see .github/workflows/sync_posts.yml
"""

import sys
import html as html_lib
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("requests is not installed. Run: pip install requests")

RSS_URL     = "https://nycuriosity.substack.com/feed"
WRITING_HTML = Path(__file__).parent.parent / "writing" / "index.html"
ARCHIVE_MARKER = '<div class="archive-list" id="archive">'


# ── Category heuristics ──────────────────────────────────────────────────────
# Checked in order; first match wins.
RULES = [
    # Community Board — checked first so "Parks Committee" lands here, not Parks
    ("cb3", "Community Board", [
        "community board", "parks committee", "cb3",
        "demystifying nyc community board",
    ]),
    # Parks & Environment
    ("parks", "Parks &amp; Environment", [
        "east river park", " park ", "tree", "ginkgo", "escr",
        "coastal resiliency", "garden", "playground", "greenway",
    ]),
    # Transit & Streets
    ("transit", "Transit &amp; Streets", [
        "street", "bike", "bus lane", "transit", "subway", "ibx",
        "interborough", "canal", "avenue", "scaffold", "sidewalk",
        "open street", "parking", "traffic", "pedestrian",
        "low traffic", "greenway",
    ]),
    # Budget & Policy
    ("budget", "Budget &amp; Policy", [
        "budget", " tax", "fiscal", "ibo ", "charter", "civil service",
        "comptroller", "fund", "revenue", "job growth", "economy",
        "economic", "hiring", "cso", "savings",
    ]),
]

def categorize(title: str) -> tuple[str, str]:
    t = title.lower()
    for cat_id, cat_label, keywords in RULES:
        if any(kw in t for kw in keywords):
            return cat_id, cat_label
    return "essay", "Essay &amp; Profile"


# ── Date formatting ──────────────────────────────────────────────────────────
def format_date(date_str: str) -> str:
    try:
        dt = parsedate_to_datetime(date_str)
        return f"{dt.strftime('%b')} '{dt.strftime('%y')}"
    except Exception:
        return ""


# ── HTML entry builder ───────────────────────────────────────────────────────
def build_entry(link: str, title: str, date_str: str) -> str:
    cat_id, cat_label = categorize(title)
    date_fmt = format_date(date_str)
    safe_title = html_lib.escape(title)
    return (
        f'        <a class="archive-item" data-cat="{cat_id}" '
        f'href="{link}" target="_blank" rel="noopener">\n'
        f'          <span class="archive-item-date">{date_fmt}</span>\n'
        f'          <span class="archive-title">{safe_title}</span>\n'
        f'          <span class="archive-tag">{cat_label}</span>\n'
        f'        </a>'
    )


# ── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    # Fetch RSS
    print(f"Fetching {RSS_URL} …")
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; NYCuriosity-sync/1.0; "
                "+https://github.com/TalR24/talroded_personal)"
            )
        }
        resp = requests.get(RSS_URL, timeout=15, headers=headers)
        resp.raise_for_status()
    except Exception as e:
        sys.exit(f"Failed to fetch RSS feed: {e}")

    root = ET.fromstring(resp.content)
    items = root.findall(".//item")
    print(f"Found {len(items)} items in feed.")

    # Read current HTML
    html = WRITING_HTML.read_text(encoding="utf-8")

    # Find new posts (not yet in the HTML)
    new_entries = []
    for item in items:
        link_el = item.find("link")
        title_el = item.find("title")
        date_el  = item.find("pubDate")
        if link_el is None or title_el is None:
            continue
        link  = (link_el.text or "").strip()
        title = (title_el.text or "").strip()
        date  = (date_el.text or "").strip() if date_el is not None else ""

        # Skip if URL already present anywhere in the file
        if link in html:
            continue

        new_entries.append(build_entry(link, title, date))
        print(f"  + New post: {title}")

    if not new_entries:
        print("No new posts. Nothing to update.")
        return

    # Insert new entries right after the opening archive div tag (top of list)
    insertion = "\n" + "\n".join(new_entries) + "\n"
    updated_html = html.replace(
        ARCHIVE_MARKER,
        ARCHIVE_MARKER + insertion,
        1,  # replace only the first occurrence
    )

    if updated_html == html:
        print("Warning: marker not found in HTML. No changes written.")
        return

    WRITING_HTML.write_text(updated_html, encoding="utf-8")
    print(f"Done. Added {len(new_entries)} new post(s) to {WRITING_HTML}.")


if __name__ == "__main__":
    main()
