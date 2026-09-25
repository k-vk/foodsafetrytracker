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

## Important production limitation
This starter does **not** claim fully autonomous legal/evidentiary verification. It uses deterministic extraction and source rules. Before treating it as a production public-record system, add an LLM structured-extraction/evidence-validation step, stronger entity resolution, official-source adapters/APIs where available, and legal/privacy review.

## Browser-only installation
1. Create a new **public** GitHub repository.
2. Upload the contents of this ZIP while preserving the folder structure.
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
