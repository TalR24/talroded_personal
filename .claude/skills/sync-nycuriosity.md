---
name: sync-nycuriosity
description: Use this skill when the user says they published a new post on Substack or NYCuriosity, mentions pushing a new post, asks to sync the writing archive, or says something like "just published" or "new post is live". Runs the local sync script to pull new posts into writing/index.html and pushes to GitHub.
---

# Sync NYCuriosity Posts

When the user has published a new post on NYCuriosity/Substack, run the local sync flow to update the writing archive on talroded.nycuriosity.com.

## Steps

1. Run the sync script from the repo root:
   ```
   python /Users/troded/Desktop/talroded_personal/scripts/sync_posts.py
   ```

2. Check if `writing/index.html` was modified:
   ```
   git -C /Users/troded/Desktop/talroded_personal diff --name-only
   ```

3. **If changes were made**: commit and push:
   ```
   git -C /Users/troded/Desktop/talroded_personal add writing/index.html
   git -C /Users/troded/Desktop/talroded_personal commit -m "sync: add new NYCuriosity post(s)"
   git -C /Users/troded/Desktop/talroded_personal push
   ```

4. **If no changes**: report back that no new posts were found (all posts already in the archive).

## Notes

- The script fetches from `https://nycuriosity.substack.com/api/v1/posts?limit=25`
- It skips posts whose `canonical_url` is already present anywhere in `writing/index.html`
- New posts are inserted at the top of `<div class="archive-list" id="archive">` (newest-first order)
- Auto-categorizes by title keywords: CB3 → Parks → Transit → Budget → Essay (fallback)
- The GitHub Actions cron was removed because Substack blocks CI IP ranges; this local flow is the intended path
