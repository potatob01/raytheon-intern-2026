import requests
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv

load_dotenv()

data = []

with open("data.csv", "r") as file:
    # Throw out first two header rows
    file.readline()
    file.readline()

    # Iterate over each row and store into 2d array "data"
    for line in file:
        # strip() removes trailing newline
        data.append(line.strip().split(","))

key = input("Please enter a network activity name: ")

found = False
hours = None

for line in data:
    if line[4] == key:
        hours = line[7]
        print(f"Activity {key} is worth {hours} hours.")
        found = True
        break

if not found:
    print(f"Activity {key} was not found in the given data.")

# Updating Jira fields

JIRA_BASE_URL = "https://tt-rtx-26.atlassian.net"
JIRA_EMAIL = os.getenv("EMAIL")
JIRA_API_TOKEN = os.getenv("API_KEY")
EPIC_KEY = "KAN-5"
ACTUAL_HOURS_FIELD = "customfield_10104"

def update_epic_hours(epic_key, value):
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{epic_key}"

    payload = {
        "fields": {
            ACTUAL_HOURS_FIELD: float(value)
        }
    }

    response = requests.put(
        url,
        json=payload,
        auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )

    # A successful PUT to update an issue returns 204 No Content
    if response.status_code == 204:
        print(f"Successfully set Actual Hours = {value} on {epic_key}.")
    else:
        print(f"Failed to update {epic_key}: "
              f"{response.status_code} {response.text}")

if found:
    update_epic_hours(EPIC_KEY, hours)
