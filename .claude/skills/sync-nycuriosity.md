---
name: sync-nycuriosity
description: Use this skill when the user says they published a new post on Substack or NYCuriosity, mentions pushing a new post, asks to sync the writing archive, or says something like "just published" or "new post is live". Runs the local sync script to pull new posts into writing/index.html, refreshes the embedded post counts, and pushes to GitHub.
---

# Sync NYCuriosity Posts

When Tal has published a new post, update the writing archive on talroded.nycuriosity.com from a local checkout (`/Users/troded/nycur/personal_website`). Substack blocks GitHub Actions IPs, so this runs locally; `.github/workflows/sync_posts.yml` is manual dispatch only.

## Steps

1. Pull first: `git -C /Users/troded/nycur/personal_website pull`.

2. Run the sync script:
   ```
   python3 /Users/troded/nycur/personal_website/scripts/sync_posts.py
   ```

3. Refresh the embedded post counts ("View all N posts", "All N posts") and the copy report:
   ```
   python3 /Users/troded/nycur/personal_website/scripts/copy_check.py
   ```
   Read `copy_reports/latest.md`. The "Needs a human" section lists banned strings or stale descriptors to fix by hand.

4. Check what changed:
   ```
   git -C /Users/troded/nycur/personal_website status --short
   ```

5. If `writing/index.html` (and any file `copy_check.py` updated, usually `index.html` and `profile_facts.json`) changed, stage those explicit paths, never `git add .`, then commit and push:
   ```
   git -C /Users/troded/nycur/personal_website add writing/index.html index.html profile_facts.json copy_reports/latest.md
   git -C /Users/troded/nycur/personal_website commit -m "sync: add new NYCuriosity post(s)"
   git -C /Users/troded/nycur/personal_website push
   ```
   Add the dated `copy_reports/copy_check_YYYY-MM-DD.md` path if one was written. If a new page was added, also run `python3 seo/build_sitemap.py --site personal` from `data_website/`.

6. If nothing changed, report that all posts are already in the archive.

## Notes

- The script reads `https://nycuriosity.substack.com/api/v1/archive?sort=new&limit=25`, the public endpoint. It returns only a subset of posts (43 of 70 on Sep 10 2026), so use it only to insert new posts, never to count or audit the archive. Enumerate the full archive with the logged-in Substack session.
- It skips posts whose `canonical_url` is already in `writing/index.html` and inserts new rows at the top of `<div class="archive-list" id="archive">`, newest first.
- Categories come from each post's Substack tags (`postTags`): State Capacity, Infrastructure & Streets, Policy & Economics, Civic Tech, CB3 Reports. A title keyword fallback applies only to untagged posts.
- The weekly `copy_check.yml` Action runs `copy_check.py --ci`, which skips the Substack step; the local run in step 3 is where post counts reconcile.
