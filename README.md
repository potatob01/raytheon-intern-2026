# Jira Epic Sync

Keeps Jira Epics in sync with a spreadsheet of network activities and their
logged hours. Each unique network activity in the spreadsheet maps to one Epic
in Jira; the script creates missing Epics and keeps their **Actual Hours** up to
date, with change detection and conflict handling so a scheduled run won't clobber
edits made directly in Jira.

It runs automatically once a week via GitHub Actions, and can also be run by hand.

## How it works

1. **Read the spreadsheet** (`data.xlsx`). Two header rows are skipped. For each
   row, the network activity is read from column E and the hours from column H.
2. **Validate and de-duplicate.** Rows with a missing activity name, missing or
   non-numeric hours, negative hours, or hours above 100,000 are skipped with a
   warning. For duplicate activities, the first occurrence wins.
3. **Fetch existing Epics** from the `KAN` project and match them to spreadsheet
   activities via the *Network Activity* custom field.
4. **Reconcile each activity:**
   - **New activity** → create an Epic named `Epic N` (next sequential number)
     and set its Network Activity and Actual Hours.
   - **Sheet changed** → update the Epic's Actual Hours.
   - **Jira changed, sheet unchanged** → the spreadsheet is treated as the source
     of truth, so the Jira value is restored to the sheet value.
   - **Both changed to different values** → logged as a **conflict** and skipped;
     resolve it manually, then re-run.
   - **Nothing changed** → left as-is.
5. **Save a snapshot** (`snapshot.json`) of the last-synced hours per activity.
   This is what lets the next run tell *which* side changed.

## Requirements

- Python 3.12
- A Jira account with API access to the `KAN` project on
  `https://tt-rtx-26.atlassian.net`

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root with your Jira credentials:

```
EMAIL=you@example.com
API_KEY=your_jira_api_token
```

Generate an API token at
<https://id.atlassian.com/manage-profile/security/api-tokens>. The `.env` file is
git-ignored — do not commit it.

## Usage

Put your data in `data.xlsx` (see [Spreadsheet format](#spreadsheet-format)), then:

```bash
python main.py
```

The run logs what it does — Epics created, hours updated, rows skipped, and any
conflicts found. Nothing is written to Jira for invalid rows or unresolved
conflicts.

## Spreadsheet format

`data.xlsx` is read with these assumptions:

| Setting            | Value                          |
| ------------------ | ------------------------------ |
| Header rows        | First 2 rows are skipped       |
| Network activity   | Column E (5th column)          |
| Hours              | Column H (8th column)          |

Only those two columns are used; other columns are ignored. If your layout
differs, adjust `NETWORK_ACTIVITY_COLUMN`, `HOURS_COLUMN`, and `HEADER_ROW_COUNT`
at the top of `main.py`.

## Automation

`.github/workflows/sync-epics.yml` runs the sync **every Monday at 13:00 UTC
(9am Eastern)** and can also be triggered manually from the Actions tab
(*Run workflow*). After each run it commits the updated `snapshot.json` back to
the repo.

The workflow reads credentials from two GitHub Actions secrets — set these under
**Settings → Secrets and variables → Actions**:

- `JIRA_EMAIL`
- `JIRA_API_KEY`

## Files

| File                              | Purpose                                             |
| --------------------------------- | --------------------------------------------------- |
| `main.py`                         | The sync script                                     |
| `data.xlsx`                       | Source spreadsheet of activities and hours          |
| `snapshot.json`                   | Last-synced state, used for change detection        |
| `requirements.txt`                | Python dependencies                                 |
| `.github/workflows/sync-epics.yml`| Scheduled GitHub Actions workflow                   |

## Configuration reference

These constants at the top of `main.py` control the Jira target and can be
changed if the project or custom fields differ:

- `JIRA_BASE_URL` — Jira site URL
- `PROJECT_KEY` — target project (`KAN`)
- `JiraClient.ACTUAL_HOURS_FIELD` — custom field ID for Actual Hours
- `JiraClient.NETWORK_ACTIVITY_FIELD` — custom field ID for Network Activity
