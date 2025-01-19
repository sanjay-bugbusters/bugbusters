import os
import requests
import json
from dotenv import load_dotenv
from pymongo import MongoClient
from io import BytesIO
from docx import Document

load_dotenv()

JQL_QUERY = 'issuetype = Bug AND status = Done'

mongo_client = MongoClient(f"mongodb+srv://{os.environ['USER_NAME']}:{os.environ['PASSWORD']}@issues.tbatd.mongodb.net/")
db = mongo_client[os.environ['DB_NAME']]
collection = db['defect_cause']

def get_done_bugs():
    url = f"{os.environ['JIRA_URL']}/rest/api/3/search"
    headers = {"Content-Type": "application/json"}
    auth = (os.environ['JIRA_EMAIL'], os.environ['JIRA_API_TOKEN'])

    payload = {
        "jql": JQL_QUERY,
        "fields": ["summary", "attachment", "assignee"],
        "maxResults": 1000
    }

    response = requests.post(url, json=payload, headers=headers, auth=auth)
    response.raise_for_status()
    return response.json()["issues"]

def parse_rca_to_json(rca_response):
    text = rca_response.get("text", "")
    owner = rca_response.get("assignee", "Unassigned")
    bug_id = rca_response.get("bug_id", "")
    bug_url = rca_response.get("bug_url", "")

    sections = {}
    current_section = None

    for line in text.splitlines():
        if line.strip() == "":
            continue
        if line.endswith(":") or line.lower() in ["defect summary", "description", "detailed root cause", "error logs", "analysis artifacts", "detailed solution"]:
            current_section = line.strip(":").strip()
            sections[current_section] = []
        elif current_section:
            sections[current_section].append(line.strip())

    for key in sections:
        sections[key] = " ".join(sections[key])

    parsed_json = {}
    for section, content in sections.items():
        if "logs" in section.lower():
            parsed_json.setdefault("rootCause", {}).setdefault("analysis", {})["logs"] = content
        elif "xml" in section.lower() or "artifacts" in section.lower():
            parsed_json.setdefault("rootCause", {}).setdefault("analysis", {}).setdefault("xml_files", []).append({
                "name": "Example.xml",
                "content": content
            })
        elif "root cause" in section.lower():
            parsed_json.setdefault("rootCause", {})["description"] = content
        elif "solution" in section.lower():
            parsed_json["solution"] = content
        else:
            parsed_json[section] = content

    parsed_json["owner"] = owner
    parsed_json["bug_id"] = bug_id
    parsed_json["bug_url"] = bug_url

    return parsed_json

def process_and_store_rca(issue_key, bug_url, assignee, attachment):
    print(f"Processing {attachment['filename']} from {issue_key}...")
    response = requests.get(attachment["content"], auth=(os.environ['JIRA_EMAIL'], os.environ['JIRA_API_TOKEN']))
    response.raise_for_status()

    if attachment["filename"].endswith(".docx"):
        try:
            file_stream = BytesIO(response.content)
            doc = Document(file_stream)
            rca_content = {
                "text": "\n".join([paragraph.text for paragraph in doc.paragraphs]),
                "bug_id": issue_key,
                "bug_url": bug_url,
                "assignee": assignee
            }
        except Exception as e:
            print(f"Failed to process {attachment['filename']} as .docx: {e}")
            return None
    else:
        try:
            rca_content = {
                "text": response.text,
                "bug_id": issue_key,
                "bug_url": bug_url,
                "assignee": assignee
            }
        except Exception as e:
            print(f"Failed to parse {attachment['filename']} as JSON: {e}")
            return None

    parsed_json = parse_rca_to_json(rca_content)

    existing_document = collection.find_one({"bug_id": issue_key})
    if existing_document:
        print(f"Document for bug_id {issue_key} already exists in MongoDB. Skipping.")
        return None

    collection.insert_one(parsed_json)
    print(f"Stored RCA document for {issue_key} in MongoDB.")
    return parsed_json

def load_data_from_jira():
    bugs = get_done_bugs()
    print(f"Found {len(bugs)} bugs with status 'Done'.")

    for bug in bugs:
        issue_key = bug["key"]
        bug_url = f"{os.environ['JIRA_URL']}/browse/{issue_key}"
        assignee = bug["fields"].get("assignee", {})
        assignee_name = assignee.get("displayName", "Unassigned") if assignee else "Unassigned"
        attachments = bug["fields"].get("attachment", [])

        for attachment in attachments:
            if "RCA" in attachment["filename"]:
                process_and_store_rca(issue_key, bug_url, assignee_name, attachment)

    print("Processing complete.")
