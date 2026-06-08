import requests
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv

load_dotenv()


class CSVLoader:
    """Handles reading and parsing a CSV file, skipping the first two header rows."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.data = []

    def load(self) -> list:
        """Reads the CSV file and returns its contents as a 2D list."""
        with open(self.filepath, "r") as file:
            file.readline()  # Skip first header row
            file.readline()  # Skip second header row
            for line in file:
                self.data.append(line.strip().split(","))
        return self.data


class ActivityFinder:
    """Searches parsed CSV data for a network activity by name."""

    NAME_COL = 4   # Column index for activity name
    HOURS_COL = 7  # Column index for hours value

    def __init__(self, data: list):
        self.data = data

    def find(self, key: str) -> str | None:
        """Returns the hours for the given activity name, or None if not found."""
        for line in self.data:
            if line[self.NAME_COL] == key:
                return line[self.HOURS_COL]
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


EPIC_KEY = "KAN-5"

# Load and parse the CSV data
loader = CSVLoader("data.csv")
data = loader.load()
finder = ActivityFinder(data)

# Initialize the Jira client using credentials from the .env file
jira = JiraClient(
    base_url="https://tt-rtx-26.atlassian.net",
    email=os.getenv("EMAIL"),
    api_token=os.getenv("API_KEY"),
)

# Prompt the user and search for the activity
key = input("Please enter a network activity name: ")
hours = finder.find(key)

# Update Jira if the activity was found, otherwise notify the user
if hours is not None:
    print(f"Activity {key} is worth {hours} hours.")
    jira.update_epic_hours(EPIC_KEY, hours)
else:
    print(f"Activity {key} was not found in the given data.")