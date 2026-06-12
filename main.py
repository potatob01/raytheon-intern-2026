import os
import csv
import re

import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

NETWORK_ACTIVITY_COLUMN = 4
HOURS_COLUMN = 7
HEADER_ROW_COUNT = 2

JIRA_BASE_URL = "https://tt-rtx-26.atlassian.net"
PROJECT_KEY = "KAN"
EPIC_ISSUE_TYPE = "Epic"

EPIC_NAME_PATTERN = re.compile(r"^Epic (\d+)$")


class CSVLoader:
    """Handles reading and parsing a CSV file, skipping the first two header rows."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.data = []

    def load(self) -> list:
        """Reads the CSV file and returns its contents as a 2D list."""
        with open(self.filepath, "r", newline="") as file:
            reader = csv.reader(file)
            for _ in range(HEADER_ROW_COUNT):
                next(reader, None)
            self.data = [row for row in reader]
        return self.data


class ActivityFinder:
    """Extracts network-activity-to-hours pairs from parsed CSV data."""

    def __init__(self, data: list):
        self.data = data

    def unique_activities(self) -> dict:
        """Returns an ordered mapping of {network activity: hours}.

        Rows without a network activity name are skipped. When the same
        activity appears more than once, the first occurrence wins.
        """
        activities = {}
        for line in self.data:
            # Guard against short/ragged rows in the CSV.
            if len(line) <= max(NETWORK_ACTIVITY_COLUMN, HOURS_COLUMN):
                continue

            name = line[NETWORK_ACTIVITY_COLUMN].strip()
            if not name or name in activities:
                continue

            raw_hours = line[HOURS_COLUMN].strip()
            try:
                hours = float(raw_hours) if raw_hours else 0.0
            except ValueError:
                hours = 0.0

            activities[name] = hours
        return activities


class JiraClient:
    """Handles communication with the Jira REST API."""

    ACTUAL_HOURS_FIELD = "customfield_10104"      # Jira custom field ID for actual hours
    NETWORK_ACTIVITY_FIELD = "customfield_10105"  # Jira custom field ID for network activity

    def __init__(self, base_url: str, email: str, api_token: str):
        self.base_url = base_url
        self.auth = HTTPBasicAuth(email, api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def get_epics(self, project_key: str) -> list:
        """Returns all epics in the project as a list of dicts.

        Each dict contains: key, summary, network_activity, hours.
        Handles token-based pagination of the Jira search API.
        """
        url = f"{self.base_url}/rest/api/3/search/jql"
        jql = f"project = {project_key} AND issuetype = {EPIC_ISSUE_TYPE}"
        fields = ["summary", self.NETWORK_ACTIVITY_FIELD, self.ACTUAL_HOURS_FIELD]

        epics = []
        next_page_token = None
        while True:
            payload = {"jql": jql, "fields": fields, "maxResults": 100}
            if next_page_token:
                payload["nextPageToken"] = next_page_token

            response = requests.post(url, json=payload, auth=self.auth, headers=self.headers)
            if response.status_code != 200:
                print(f"Failed to fetch epics: {response.status_code} {response.text}")
                break

            body = response.json()
            for issue in body.get("issues", []):
                issue_fields = issue.get("fields", {})
                epics.append({
                    "key": issue["key"],
                    "summary": issue_fields.get("summary"),
                    "network_activity": issue_fields.get(self.NETWORK_ACTIVITY_FIELD),
                    "hours": issue_fields.get(self.ACTUAL_HOURS_FIELD),
                })

            if body.get("isLast", True):
                break
            next_page_token = body.get("nextPageToken")
            if not next_page_token:
                break

        return epics

    def create_epic(self, project_key: str, summary: str) -> str | None:
        """Creates a new epic and returns its key, or None on failure."""
        url = f"{self.base_url}/rest/api/3/issue"
        payload = {
            "fields": {
                "project": {"key": project_key},
                "issuetype": {"name": EPIC_ISSUE_TYPE},
                "summary": summary,
            }
        }
        response = requests.post(url, json=payload, auth=self.auth, headers=self.headers)

        if response.status_code == 201:
            key = response.json()["key"]
            print(f"Created epic {key} ({summary}).")
            return key

        print(f"Failed to create epic '{summary}': {response.status_code} {response.text}")
        return None

    def update_epic_fields(self, epic_key: str, hours: float = None, network_activity: str = None) -> bool:
        """Updates the hours and/or network activity custom fields on an epic."""
        fields = {}
        if hours is not None:
            fields[self.ACTUAL_HOURS_FIELD] = float(hours)
        if network_activity is not None:
            fields[self.NETWORK_ACTIVITY_FIELD] = network_activity

        if not fields:
            return True

        url = f"{self.base_url}/rest/api/3/issue/{epic_key}"
        response = requests.put(url, json={"fields": fields}, auth=self.auth, headers=self.headers)

        # A successful PUT to update an issue returns 204 No Content
        if response.status_code == 204:
            updated = ", ".join(f"{k}={v}" for k, v in [("Network Activity", network_activity), ("Actual Hours", hours)] if v is not None)
            print(f"Updated {epic_key}: {updated}.")
            return True

        print(f"Failed to update {epic_key}: {response.status_code} {response.text}")
        return False


def next_epic_number(epics: list) -> int:
    """Returns the next available number for the 'Epic <n>' naming scheme."""
    highest = 0
    for epic in epics:
        match = EPIC_NAME_PATTERN.match((epic.get("summary") or "").strip())
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def hours_match(existing, new) -> bool:
    """Returns True if the epic's current hours already equal the new value."""
    if existing is None:
        return False
    try:
        return float(existing) == float(new)
    except (TypeError, ValueError):
        return False


def main():
    load_dotenv()

    loader = CSVLoader("data.csv")
    data = loader.load()
    finder = ActivityFinder(data)
    activities = finder.unique_activities()

    if not activities:
        print("No network activities found in the data.")
        return

    jira = JiraClient(
        base_url=JIRA_BASE_URL,
        email=os.getenv("EMAIL"),
        api_token=os.getenv("API_KEY"),
    )

    # Index existing epics by their Network Activity field for quick lookup.
    epics = jira.get_epics(PROJECT_KEY)
    epics_by_activity = {
        epic["network_activity"]: epic
        for epic in epics
        if epic["network_activity"]
    }
    epic_counter = next_epic_number(epics)

    print(f"Processing {len(activities)} network activities against {len(epics)} existing epics.\n")

    for activity, hours in activities.items():
        existing = epics_by_activity.get(activity)

        if existing:
            # Epic already tracks this activity: only refresh its hours.
            if hours_match(existing.get("hours"), hours):
                print(f"{existing['key']} already up to date for '{activity}' ({hours} hours).")
            else:
                jira.update_epic_fields(existing["key"], hours=hours)
            continue

        # No epic tracks this activity yet: create one and populate both fields.
        summary = f"Epic {epic_counter}"
        epic_counter += 1

        new_key = jira.create_epic(PROJECT_KEY, summary)
        if new_key is None:
            continue

        jira.update_epic_fields(new_key, hours=hours, network_activity=activity)

    print("\nDone.")


if __name__ == "__main__":
    main()
