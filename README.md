# Food Safety Tracker — India

## Product principle

This is a public **food-safety record**, not a public blacklist.

The tracker is designed around:
- consumer information;
- traceable evidence;
- long-term incident history;
- pattern analysis;
- positive compliance information;
- correction / reopening history.

### Evidence hierarchy

1. Official inspection orders, notices, seizure records and laboratory reports.
2. Official FSSAI/state/municipal publications and official government social accounts.
3. Reputable news reports used for discovery and, where necessary, clearly labelled as reported information.

Anonymous allegations, user reviews and unverified social-media claims are not treated as findings.

### Legal / editorial safeguards

- Every incident has a source URL and source type.
- Every record has a verification status.
- The site uses neutral descriptions: it reports what an authority/source says rather than declaring a business “unsafe” or “bad”.
- Follow-up compliance, licence restoration and passed/compliant inspections are retained.
- No “worst restaurants”, safety scores, shame rankings or permanent labels.
- Do not infer guilt from a sample collection; laboratory results and adjudicated outcomes are separate fields.
- A business name should only be published when the source identifies the establishment clearly.
- Maintain a correction/takedown contact and an audit trail of changes.
- For legal review before public launch, obtain India-specific advice on defamation, intermediary/publisher obligations, privacy, fair comment, and republication of official allegations.

## Daily automation

GitHub Actions runs at 08:00 IST:
News/official discovery -> extraction -> categorization -> deduplication -> publish or quarantine -> commit.

`data/review_queue.csv` holds uncertain automated records.

## Next production upgrade

Add an AI structured-extraction step that returns:
restaurant, exact location, inspection date, authority, findings, action, evidence excerpt, source type, confidence, and whether the statement is an allegation, official finding, lab-confirmed result, or final adjudication.

Only high-confidence records with adequate source evidence should publish automatically.
