# Food Safety Tracker — browser-ready GitHub Pages starter

## What this version does
- Daily GitHub Actions update at 08:00 IST.
- Manual update through **Actions → Update and Deploy Food Safety Tracker → Run workflow**.
- Collects food-safety discovery results from Google News RSS.
- Fetches article text and applies conservative rule-based evidence/category checks.
- Publishes only official-source records or records with explicit action + finding signals.
- Keeps uncertain records in `data/review_queue.csv`.
- Turns queued news articles into records (see **Automatic extraction** below).
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
- Records table: S No, restaurant, location, inspection date, findings, action taken, authority, follow-up status, source. Restaurant names open every record for that establishment (`#r=<id>`); dates open every establishment acted on that day with its sources (`#d=<date>`). On phones each row becomes a card.
- Rows written by the automatic extraction step carry an "Auto-extracted" tag.
- Method section explaining the source hierarchy, publication rule and evidence principles.
- Light/dark theme, mobile layout, and clear empty/error states.
- Preview the layout with fictional records by adding `?demo=1` to the URL (shown under a "demo mode" banner; never shown otherwise).

## Update script changes (`scripts/update_tracker.py`)
- Decodes Google News links to the publisher URL (via `googlenewsdecoder`); items whose link can't be resolved are skipped rather than published.
- Auto-publishes only official-source items. News items found by the daily run go to `data/review_queue.csv`; the extraction step then turns those that name establishments into records.
- Reads each feed newest-first, and fails the run if the Google News decoder cannot load (pin `selectolax<1.0`).
- Expanded list of recognised news domains (includes all outlets cited in the curated records).
- De-duplicates on source URL + establishment name, and skips articles already covered by curated or review-queue records, so repeat runs don't add duplicates.
- Sorts the published dataset newest first.

## Automatic extraction (`scripts/extract_records.py`)
Runs in the daily workflow after `update_tracker.py`, on every queued news article from the last 30 days that it has not processed before.

**Rules (default, no API key needed) — `scripts/rule_extract.py`.** Indian food-safety reports name establishments in lists after a trigger phrase ("The establishments whose licences were suspended include Hotel X at Tolichowki, Y Restaurant at Santosh Nagar…", "…took action against M/s A, M/s B Pvt Ltd (Brand)…", "A and B in Kamareddy district; and C in Nizamabad district"). The rules find those sentences and split them into establishments, attaching:
- the area or district given with each name, mapped to a city and state through a built-in place list (localities such as Gachibowli or Bandra are recognised as areas, not names);
- the action the sentence describes (suspension, cancellation, show-cause or improvement notice, closure, sealing);
- the authority (TG SAFE, FDA Maharashtra, KMC, GHMC, state food safety departments);
- the inspection date when the article states one ("on Saturday", "(October 13)");
- findings only from a sentence elsewhere in the article that describes that establishment; otherwise "Findings for this establishment were not itemised in the report."

The city comes from the establishment's own area or district, the text introducing the list, or the article's dateline/headline — the dateline only for state or city authorities, and never when the article's other establishments are in other cities. Rules miss establishments named only in free prose. Tested on 43 queued articles: every establishment list in the reports was picked up, general-news articles produced nothing.

**Claude (optional).** If the `ANTHROPIC_API_KEY` repository secret is set, the same step uses Claude (`claude-opus-5-5`, structured JSON output, up to 15 articles per run) instead, which also catches establishments described in prose.

Either way, every result is checked against the article before it is published:
- the establishment's name must appear in the article text, and city and state must be present;
- the quote is kept only if it appears word for word in the article;
- dates must be valid and not in the future;
- records for an establishment already in the tracker (same name — ignoring brackets, company suffixes and words like hotel/restaurant — in the same city within 7 days) are skipped.

Published rows are marked **"Auto-extracted (rule-based) from news report — not reviewed"** (or "Auto-extracted from news report" for Claude). Articles that produced records leave the review queue; every processed article is logged in `data/extraction_log.json`, with the reason for any skipped record.

## Important production limitation
This is not legal or evidentiary verification. Auto-extracted records can misread an article, so they are tagged and should be reviewed against the source. Before treating the site as a production public-record system, add human review of auto-extracted rows, stronger entity resolution, official-source adapters/APIs where available, and legal/privacy review.

## Data model
The incident is the core public record. Follow-up and corrective-action history should be preserved rather than leaving a permanent negative label.

## Evidence principles
- Prefer official FSSAI/state/municipal records.
- News is primarily discovery unless sufficiently supported.
- Do not infer guilt from sample collection.
- Preserve evidence excerpts and source URLs.
- Keep compliance/correction outcomes visible.
- Do not create “worst restaurants”, safety scores, shame rankings or permanent labels.
