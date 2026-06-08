import csv
import os

import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Column positions within data.csv (0-indexed)
NETWORK_ACTIVITY_COLUMN = 4
HOURS_COLUMN = 7
HEADER_ROW_COUNT = 2


class ActivityRepository:
    """Loads network activities from a CSV file and looks up their hours."""

    def __init__(self, csv_path):
        self.csv_path = csv_path
        self._rows = self._load()

    def _load(self):
        with open(self.csv_path, "r", encoding="utf-8-sig", newline="") as file:
            reader = csv.reader(file)
            rows = list(reader)
        # Skip the two header rows that label each column.
        return rows[HEADER_ROW_COUNT:]

    def find_hours(self, activity_name):
        """Return the hours for an activity name, or None if not found."""
        for row in self._rows:
            if len(row) > HOURS_COLUMN and row[NETWORK_ACTIVITY_COLUMN] == activity_name:
                return row[HOURS_COLUMN]
        return None


class JiraClient:
    """Minimal Jira REST client for updating an epic's Actual Hours field."""

    ACTUAL_HOURS_FIELD = "customfield_10104"

    def __init__(self, base_url, email, api_token):
        self.base_url = base_url.rstrip("/")
        self.auth = HTTPBasicAuth(email, api_token)

    def update_epic_hours(self, epic_key, hours):
        """Set the Actual Hours field on an epic. Returns True on success."""
        url = f"{self.base_url}/rest/api/3/issue/{epic_key}"
        payload = {"fields": {self.ACTUAL_HOURS_FIELD: float(hours)}}

        response = requests.put(
            url,
            json=payload,
            auth=self.auth,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

        # A successful PUT to update an issue returns 204 No Content.
        if response.status_code == 204:
            print(f"Successfully set Actual Hours = {hours} on {epic_key}.")
            return True

        print(f"Failed to update {epic_key}: {response.status_code} {response.text}")
        return False


def main():
    load_dotenv()

    repository = ActivityRepository("data.csv")

    activity_name = input("Please enter a network activity name: ")
    hours = repository.find_hours(activity_name)

    if hours is None:
        print(f"Activity {activity_name} was not found in the given data.")
        return

    print(f"Activity {activity_name} is worth {hours} hours.")

    jira = JiraClient(
        base_url="https://tt-rtx-26.atlassian.net",
        email=os.getenv("EMAIL"),
        api_token=os.getenv("API_KEY"),
    )
    jira.update_epic_hours("KAN-5", hours)


if __name__ == "__main__":
    main()
