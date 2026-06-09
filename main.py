import os
import csv

import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

NETWORK_ACTIVITY_COLUMN = 4
HOURS_COLUMN = 7
HEADER_ROW_COUNT = 2


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
    """Searches parsed CSV data for a network activity by name."""

    def __init__(self, data: list):
        self.data = data

    def find(self, key: str) -> str | None:
        """Returns the hours for the given activity name, or None if not found."""
        for line in self.data:
            if line[NETWORK_ACTIVITY_COLUMN] == key:
                return line[HOURS_COLUMN]
        return None


class JiraClient:
    """Handles communication with the Jira REST API."""

    ACTUAL_HOURS_FIELD = "customfield_10104"  # Jira custom field ID for actual hours

    def __init__(self, base_url: str, email: str, api_token: str):
        self.base_url = base_url
        self.auth = HTTPBasicAuth(email, api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def update_epic_hours(self, epic_key: str, value: float) -> None:
        """Updates the Actual Hours custom field on a given Jira epic."""
        url = f"{self.base_url}/rest/api/3/issue/{epic_key}"
        payload = {
            "fields": {
                self.ACTUAL_HOURS_FIELD: float(value)
            }
        }
        response = requests.put(url, json=payload, auth=self.auth, headers=self.headers)

        # A successful PUT to update an issue returns 204 No Content
        if response.status_code == 204:
            print(f"Successfully set Actual Hours = {value} on {epic_key}.")
        else:
            print(f"Failed to update {epic_key}: {response.status_code} {response.text}")


def main():
    load_dotenv()

    EPIC_KEY = "KAN-6"

    loader = CSVLoader("data.csv")
    data = loader.load()
    finder = ActivityFinder(data)

    activity_name = input("Please enter a network activity name: ")
    hours = finder.find(activity_name)

    # Update Jira if the activity was found, otherwise notify the user
    if hours is None:
       print(f"Activity {activity_name} was not found in the given data.")
       return
    
    print(f"Activity {activity_name} is worth {hours} hours.")

    # Initialize the Jira client using credentials from the .env file
    jira = JiraClient(
       base_url="https://tt-rtx-26.atlassian.net",
       email=os.getenv("EMAIL"),
       api_token=os.getenv("API_KEY"),
   )
    jira.update_epic_hours(EPIC_KEY, hours)


if __name__ == "__main__":
   main()
