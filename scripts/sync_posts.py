"""
sync_posts.py
Fetches recent NYCuriosity posts via the Substack JSON API and inserts any
posts not already listed into writing/index.html (newest first).

WARNING: this uses the PUBLIC archive endpoint, which returns only a subset of
the publication's posts and silently drops older ones (43 of 70 on Sep 10
2026). It is safe ONLY for inserting new posts at the top of the list. Never
use it to regenerate, audit, or count the archive; that needs the logged-in
enumeration described in the reference-substack-post-api memory.

The RSS feed is read as a second source (Nov 10 2026): on Nov 5 2026 the public
archive omitted a live cross-post that the feed carried, and the sync reported
"no new posts". A post found in either source is inserted.

Run locally only:  python scripts/sync_posts.py
(Substack blocks GitHub Actions IPs, so the old sync_posts.yml workflow was
removed Nov 10 2026; copy_check.py runs this script at the session sweep.)
"""

import sys
import html as html_lib
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("requests is not installed. Run: pip install requests")

API_URL      = "https://nycuriosity.substack.com/api/v1/archive?sort=new&limit=25"
FEED_URL     = "https://www.nycuriosity.com/feed"
WRITING_HTML = Path(__file__).parent.parent / "writing" / "index.html"
ARCHIVE_MARKER = '<div class="archive-list" id="archive">'

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NYCuriosity-sync/1.0; "
                  "+https://github.com/TalR24/talroded_personal)",
    "Accept": "application/json",
}


# ── Categories, mirrored from the publication's own Substack tags ────────────
# The Substack API returns each post's real tags in `postTags`, so we map those
# instead of guessing from the title. Keyword RULES are only a fallback for a
# post that somehow has no tags yet. Canonical Substack tags (exactly five
# since Sep 10 2026, matching the homepage tabs; "Parks", "Manhattan CB3" and
# "CB Guide" were deleted):
#   State Capacity · Infrastructure & Streets · Policy & Economics ·
#   Civic Tech · CB3 Reports
# Order = Substack tab order; the first hit becomes the visible label.
CAT_FROM_TAGS = [
    ("statecap",  "State Capacity",               {"State Capacity"}),
    ("infra",     "Infrastructure &amp; Streets", {"Infrastructure & Streets"}),
    ("policy",    "Policy &amp; Economics",       {"Policy & Economics"}),
    ("civictech", "Civic Tech",                   {"Civic Tech"}),
    ("cb3",       "Community Board",             {"CB3 Reports"}),
]

# Fallback only (post with no tags): first match wins.
RULES = [
    ("cb3", "Community Board", ["community board", "parks committee", "cb3",
                                "demystifying nyc community board"]),
    ("parks", "Parks", ["east river park", " park ", "tree", "ginkgo", "escr",
                        "coastal resiliency", "garden", "playground", "greenway"]),
    ("infra", "Infrastructure &amp; Streets", ["street", "bike", "bus lane", "transit",
                        "subway", "ibx", "interborough", "canal", "avenue", "scaffold",
                        "sidewalk", "open street", "parking", "traffic", "pedestrian",
                        "low traffic", "greenway", "infrastructure", "resiliency"]),
    ("statecap", "State Capacity", ["state capacity", "agency spotlight", "deputy mayor"]),
    ("civictech", "Civic Tech", ["ai ", " ai", "civic tech", "knowledge base",
                        "government is", "toolkit", "dashboard", "tracker"]),
    ("policy", "Policy &amp; Economics", ["budget", " tax", "fiscal", "ibo ", "charter",
                        "civil service", "comptroller", "fund", "revenue", "job growth",
                        "economy", "economic", "hiring", "cso", "savings", "mandates"]),
]


def categorize(title: str, post_tags=None) -> tuple[str, str]:
    """Return (data-cat tokens, visible label). Tags win; title is the fallback.

    data-cat may hold several space-separated tokens, mirroring the fact that a
    post can be tagged e.g. both Infrastructure & Streets and Civic Tech. The
    filter JS in writing/index.html splits on whitespace.
    """
    names = {t.get("name") for t in (post_tags or []) if isinstance(t, dict)}
    if names:
        hits = [(cid, label) for cid, label, want in CAT_FROM_TAGS if names & want]
        if hits:
            return " ".join(c for c, _ in hits), hits[0][1]
    t = title.lower()
    for cat_id, cat_label, keywords in RULES:
        if any(kw in t for kw in keywords):
            return cat_id, cat_label
    # No Essay filter exists on the writing page any more (retired Sep 10 2026).
    return "policy", "Policy &amp; Economics"


# ── Date formatting ──────────────────────────────────────────────────────────
def format_date(date_str: str) -> str:
    try:
        # Substack API returns ISO 8601, e.g. "2026-03-27T12:00:00.000Z"
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return f"{dt.strftime('%b')} '{dt.strftime('%y')}"
    except Exception:
        return ""


# ── HTML entry builder ───────────────────────────────────────────────────────
def build_entry(link: str, title: str, date_str: str, post_tags=None) -> str:
    cat_id, cat_label = categorize(title, post_tags)
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


# ── RSS feed (second source) ─────────────────────────────────────────────────
def feed_posts() -> list[dict]:
    """Posts from the RSS feed, shaped like the archive API's items. Never fatal."""
    try:
        resp = requests.get(FEED_URL, timeout=15, headers={**HEADERS, "Accept": "application/rss+xml"})
        resp.raise_for_status()
        items = ET.fromstring(resp.content).iter("item")
    except Exception as e:
        print(f"Warning: could not read the RSS feed ({e}); archive API only.")
        return []
    out = []
    for it in items:
        link = (it.findtext("link") or "").split("?")[0].strip()
        try:
            date = parsedate_to_datetime(it.findtext("pubDate") or "").astimezone(timezone.utc).isoformat()
        except Exception:
            date = ""
        out.append({"canonical_url": link, "title": (it.findtext("title") or "").strip(), "post_date": date})
    return out


# ── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    # Fetch posts via Substack JSON API
    print(f"Fetching {API_URL} …")
    try:
        resp = requests.get(API_URL, timeout=15, headers=HEADERS)
        resp.raise_for_status()
    except Exception as e:
        # Substack/Cloudflare blocks requests from cloud/CI IP ranges (403).
        # Run this script locally instead: python scripts/sync_posts.py
        print(f"Warning: could not fetch posts ({e}). Run locally to sync.")
        sys.exit(0)

    posts = resp.json()
    # Since about Nov 2026 the endpoint returns {"posts": [...], "nextCursor": ...}
    # instead of a bare list (paging is by cursor, no longer by offset). The old
    # list handling crashed on it and copy_check logged "no new posts".
    if isinstance(posts, dict):
        posts = posts.get("posts") or []
    if not isinstance(posts, list):
        sys.exit(f"Unexpected archive API response shape: {type(posts).__name__}")
    posts = [p for p in posts if isinstance(p, dict)]
    print(f"Found {len(posts)} posts in API response.")
    api_links = {(p.get("canonical_url") or "").strip() for p in posts}
    extra = [p for p in feed_posts() if p["canonical_url"] and p["canonical_url"] not in api_links]
    if extra:
        print(f"RSS feed carries {len(extra)} post(s) the archive API omitted.")
    # Newest first across both sources, so inserted rows keep the page's order.
    posts = sorted(posts + extra, key=lambda p: p.get("post_date") or "", reverse=True)

    # Read current HTML
    html = WRITING_HTML.read_text(encoding="utf-8")

    # Find new posts (not yet in the HTML)
    new_entries = []
    for post in posts:
        link  = (post.get("canonical_url")
                 or (f"https://www.nycuriosity.com/p/{post.get('slug')}" if post.get("slug") else "")).strip()
        title = (post.get("title") or "").strip()
        date  = (post.get("post_date") or "").strip()

        if not link or not title:
            continue

        # Skip if URL already present anywhere in the file
        if link in html:
            continue

        new_entries.append(build_entry(link, title, date, post.get("postTags")))
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
