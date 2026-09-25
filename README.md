# Food Safety Tracker — browser-ready GitHub Pages starter

## What this version does
- Daily GitHub Actions update at 08:00 IST.
- Manual update through **Actions → Update and Deploy Food Safety Tracker → Run workflow**.
- Collects food-safety discovery results from Google News RSS.
- Fetches article text and applies conservative rule-based evidence/category checks.
- Publishes only official-source records or records with explicit action + finding signals.
- Keeps uncertain records in `data/review_queue.csv`.
- Commits data changes back to the repository.
- Deploys `public/` automatically to GitHub Pages.
- Provides a searchable public interface.

## Current dataset (September 2026)
`data/food_safety_incidents.csv` and `public/food_safety_incidents.json` hold **40 curated records** (IDs `FS-2026-0001` to `FS-2026-0040`) covering June–September 2026:

- Telangana (Hyderabad — TG SAFE and Cyberabad Municipal Corporation): 33
- Maharashtra (FDA Maharashtra — Mumbai, Navi Mumbai, Pune, Chhatrapati Sambhajinagar): 6
- Karnataka (Food Safety and Drug Administration — Bengaluru): 1

All records are drawn from news reports of official action, carry the source URL and an evidence excerpt, and are marked **"News report — corroboration recommended"**. One record (Pind Punjab, Pune) documents a licence restored after full compliance.

Curation notes:
- Where a report gave findings for a drive as a whole rather than per establishment (LB Nagar, 16 Sep; five of the 24 Sep suspensions), the record says so explicitly.
- Establishments that only received improvement notices with no specific findings, and non-restaurant businesses (warehouses, supermarkets), were not added.
- Before wider publication, check evidence excerpts against the source articles and replace with official press notes where available.

## Public page (`public/index.html`)
- Summary counts, last-updated date, and filters for search, state, source type, record type (findings vs compliance) and sort order.
- Clickable finding-category counts (frequency of finding types — not a ranking of establishments).
- Record cards with authority, action, follow-up status, verification label, evidence excerpt and source link.
- Method section explaining the source hierarchy, publication rule and evidence principles.
- Light/dark theme, mobile layout, and clear empty/error states.
- Preview the layout with fictional records by adding `?demo=1` to the URL (shown under a "demo mode" banner; never shown otherwise).

## Update script changes (`scripts/update_tracker.py`)
- Decodes Google News links to the publisher URL (via `googlenewsdecoder`); items whose link can't be resolved are skipped rather than published.
- Auto-publishes only official-source items. News items found by the daily run go to `data/review_queue.csv` for a person to add the establishment, city/state and authority before moving them into the dataset.
- Expanded list of recognised news domains (includes all outlets cited in the curated records).
- De-duplicates on source URL + establishment name, and skips articles already covered by curated or review-queue records, so repeat runs don't add duplicates.
- Sorts the published dataset newest first.

## Important production limitation
This starter does **not** claim fully autonomous legal/evidentiary verification. It uses deterministic extraction and source rules. Before treating it as a production public-record system, add an LLM structured-extraction/evidence-validation step, stronger entity resolution, official-source adapters/APIs where available, and legal/privacy review.

## Browser-only installation
1. Create a new **public** GitHub repository.
2. Upload the contents of this folder while preserving the folder structure.
3. Open **Settings → Pages** and choose **GitHub Actions** as the source.
4. Open **Actions**, select **Update and Deploy Food Safety Tracker**, and click **Run workflow** once.
5. After the first successful run, GitHub Pages will publish the site.

## GitHub Pages URL
Usually:
`https://YOUR-USERNAME.github.io/YOUR-REPOSITORY/`

## Data model
The incident is the core public record. Follow-up and corrective-action history should be preserved rather than leaving a permanent negative label.

## Evidence principles
- Prefer official FSSAI/state/municipal records.
- News is primarily discovery unless sufficiently supported.
- Do not infer guilt from sample collection.
- Preserve evidence excerpts and source URLs.
- Keep compliance/correction outcomes visible.
- Do not create “worst restaurants”, safety scores, shame rankings or permanent labels.
