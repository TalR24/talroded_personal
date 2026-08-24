# talroded_personal

Personal website for Tal Roded — hosted on GitHub Pages with a custom domain.

**Live at**: [talroded.nycuriosity.com](https://talroded.nycuriosity.com)

---

## Site Structure

```
/               → Homepage (featured writing, projects grid)
/writing/       → NYCuriosity archive (64 posts, filterable by topic)
/research/      → Publications & outside writing (nav label: "Publications")
/wiki/          → Reference guides on career, data science, econ, policy, and more
/about/         → About page
/services/      → NYCuriosity Studio (paid commissions)
/resume/        → Resume page — linked from About only, NOT in the nav
```

### Writing Archive (`/writing/`)
Full archive of [NYCuriosity](https://www.nycuriosity.com/) posts. Filterable by topic:
- Transit & Streets
- Parks & Environment
- Budget & Policy
- Community Board
- Essay & Profile

### Publications (`/research/`)
Outside bylines (Streetsblog, Vital City, Reboot Democracy), peer-reviewed work, and working papers. Nav label is **Publications**; the URL stays `/research/` for link stability.

### Wiki (`/wiki/`)
Reference pages on: career advice, data science, economics courses and readings, grad school, GRE, public data, public policy, RA advice, civic tech, and more.

---

## Tech

- Plain HTML/CSS — no build step, no framework
- Shared stylesheet: `assets/style.css`
- Hosted on GitHub Pages; custom domain set via `CNAME`

## Site chrome & shared components

Header and footer markup is duplicated per page, but all styling lives in the shared `assets/style.css`. When adding a new page, copy the header/footer from an existing page.

- **Header** — dark bar with brand (`tal·roded`), nav, then a `.header-right` row of outlined `.header-icon-link` external links (GitHub, Data, **Support my work**) followed by the white `.header-cta` (`NYCuriosity ↗`).
- **Footer** — `.footer-inner` with brand, `.footer-links` nav, the `.footer-support` pill, and copyright.
- **Buy Me a Coffee** — links to `https://buymeacoffee.com/nycuriosity`, label **"Support my work"**, coffee-cup icon, `target="_blank"`. In both header (class `header-icon-link header-support`, subtle blue-tinted outline) and footer (class `footer-support`). Fills solid blue on hover.
- The old **Block Party** header link has been removed site-wide (a Block Party project card may still appear in page bodies — that's intentional, leave it).
- **Standalone pages without the shared shell** — `resume_oti_business_analysis.html` has no header/footer; skip it when propagating chrome (untracked local file, not deployed). `western-parks-planner.html` was deleted Aug 24 2026.
- **Link previews** — every shell page carries `og:image`/`twitter:card` meta pointing at `/og_card.png` (1200×630). Regenerate the card by rendering an HTML mock at that size via headless Chrome `--screenshot`.
- **Canonical NYCuriosity descriptor** — use verbatim wherever the newsletter is described: "data-driven analysis of NYC transit, streets, housing, and how the city governs itself."
- **All Substack links point at `https://www.nycuriosity.com`** (the custom domain), not `nycuriosity.substack.com`.
