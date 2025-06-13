import os
import requests
import json
from dotenv import load_dotenv
from pymongo import MongoClient
from io import BytesIO
from docx import Document
import re

load_dotenv()

JQL_QUERY = 'issuetype = Bug AND status = Done'

mongo_client = MongoClient(f"mongodb+srv://{os.environ['USER_NAME']}:{os.environ['PASSWORD']}@pocapp.aegpzjw.mongodb.net/")
db = mongo_client[os.environ['DB_NAME']]
collection = db['defect_cause_poc']

def get_done_bugs():
    url = f"{os.environ['JIRA_URL']}/rest/api/3/search"
    headers = {"Content-Type": "application/json"}
    auth = (os.environ['JIRA_EMAIL'], os.environ['JIRA_API_TOKEN'])

    payload = {
        "jql": JQL_QUERY,
        "fields": ["summary", "attachment", "assignee", "description", "comment"],
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

def extract_text_from_jira_content(content) -> str:
    """Extract plain text from Jira's structured content"""
    if not content:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        if content.get('type') == 'doc':
            # Handle Jira's Atlassian Document Format
            return extract_text_from_adf(content)
        if 'content' in content:
            text = []
            for item in content.get('content', []):
                if item.get('type') == 'text':
                    text.append(item.get('text', ''))
                elif item.get('type') == 'paragraph':
                    for child in item.get('content', []):
                        if child.get('type') == 'text':
                            text.append(child.get('text', ''))
            return ' '.join(text)
    return ""

def extract_text_from_adf(adf_content: dict) -> str:
    """Extract text from Atlassian Document Format"""
    text = []
    
    def process_content(content):
        if isinstance(content, dict):
            if content.get('type') == 'text':
                text.append(content.get('text', ''))
            elif 'content' in content:
                for item in content['content']:
                    process_content(item)
        elif isinstance(content, list):
            for item in content:
                process_content(item)
    
    process_content(adf_content)
    return ' '.join(text)

def extract_rca_from_text(text) -> dict:
    """Extract RCA information from text content."""
    # Convert input to plain text
    text = extract_text_from_jira_content(text)
    
    rca_info = {
        "description": "",
        "solution": "",
        "analysis": {"logs": ""}
    }
    
    if not text:
        return rca_info
        
    text_lower = text.lower()
    
    # Look for common RCA markers
    rca_markers = [
        "memory leak:", "memory usage:", "heap analysis:",
        "root cause:", "cause:", "reason:",
        "steps to reproduce:", "reproduction steps:",
        "solution:", "fix:", "resolution:",
        "verification steps:", "test steps:",
        "error log:", "stack trace:", "exception:"
    ]
    
    sections = {
        'description': [],
        'steps_to_reproduce': [],
        'solution': [],
        'verification': [],
        'logs': []
    }
    
    current_section = None
    lines = text.split('\n')
    
    for line in lines:
        line_lower = line.lower().strip()
        
        # Detect sections
        if "memory leak" in line_lower or "root cause" in line_lower:
            current_section = 'description'
        elif "steps to reproduce" in line_lower:
            current_section = 'steps_to_reproduce'
        elif "solution" in line_lower or "changes made" in line_lower:
            current_section = 'solution'
        elif "verification" in line_lower or "test" in line_lower:
            current_section = 'verification'
        elif any(marker in line_lower for marker in ["error", "log", "trace", "exception"]):
            current_section = 'logs'
        elif line.strip() and current_section:
            sections[current_section].append(line.strip())
    
    return {
        "description": " ".join(sections['description']),
        "analysis": {
            "logs": " ".join(sections['logs']),
            "steps_to_reproduce": " ".join(sections['steps_to_reproduce']),
            "verification_steps": " ".join(sections['verification'])
        },
        "solution": " ".join(sections['solution'])
    }

def analyze_summary(summary: str) -> dict:
    """Analyze bug summary to generate initial RCA information."""
    # Common patterns for different types of issues
    patterns = {
        'memory': ['memory leak', 'memory usage', 'memory consumption', 'heap', 'garbage collection'],
        'ui': ['button', 'click', 'tap', 'interface', 'unresponsive', 'display', 'screen', 'mobile'],
        'api': ['endpoint', 'request', 'response', 'api', 'service'],
        'data': ['database', 'data', 'record', 'null', 'missing'],
        'auth': ['login', 'authentication', 'password', 'credential', 'session'],
        'performance': ['slow', 'timeout', 'performance', 'latency', 'loading']
    }
    
    summary_lower = summary.lower()
    issue_type = None
    
    # Determine issue type
    for type_key, keywords in patterns.items():
        if any(keyword in summary_lower for keyword in keywords):
            issue_type = type_key
            break
    
    # Generate analysis based on issue type
    analysis = {
        'memory': {
            'description': "Memory leak detected in application, causing increased memory consumption over time.",
            'analysis': {
                'logs': "Memory profiling shows gradual increase in heap usage without proper cleanup."
            },
            'solution': "Implement proper resource cleanup in try-finally blocks and verify all response objects are properly disposed."
        },
        'ui': {
            'description': "Initial analysis indicates a UI/UX issue affecting user interaction with the interface.",
            'analysis': {'logs': "User interaction events not being captured or processed correctly."},
            'solution': "Investigate event handling and touch listeners on the affected UI elements."
        },
        'api': {
            'description': "Potential API integration or service communication issue.",
            'analysis': {'logs': "API endpoint communication needs to be verified."},
            'solution': "Check API endpoints and request/response handling."
        },
        'data': {
            'description': "Data handling or database interaction issue.",
            'analysis': {'logs': "Data flow and database operations need verification."},
            'solution': "Verify data persistence and retrieval operations."
        },
        'auth': {
            'description': "Authentication or session management issue.",
            'analysis': {'logs': "Authentication flow and session handling require investigation."},
            'solution': "Review authentication process and session management."
        },
        'performance': {
            'description': "Performance optimization required.",
            'analysis': {'logs': "Performance metrics indicate optimization needed."},
            'solution': "Conduct performance profiling and optimization."
        }
    }
    
    if issue_type and issue_type in analysis:
        return analysis[issue_type]
    
    return {
        'description': "Initial analysis pending. Bug reported for investigation.",
        'analysis': {'logs': "No specific error patterns identified yet."},
        'solution': "Investigation needed to determine root cause and solution."
    }

def analyze_technical_details(description: str, comments: list = None) -> dict:
    """Extract technical details from description and comments"""
    technical_info = {
        'affected_components': set(),
        'error_patterns': set(),
        'code_references': set(),
        'system_impacts': set()
    }
    
    # Combine description and comments for analysis
    full_text = extract_text_from_jira_content(description)
    
    # Process comments properly
    if comments:
        comment_texts = []
        for comment in comments:
            # Handle nested comment structure
            comment_body = comment.get('body', {})
            comment_text = extract_text_from_jira_content(comment_body)
            if comment_text:
                comment_texts.append(comment_text)
        
        if comment_texts:
            full_text += ' ' + ' '.join(comment_texts)
    
    # Extract technical components (functions, classes, endpoints)
    function_pattern = r'\b\w+\(.*?\)'
    endpoint_pattern = r'/\w+(?:/\w+)*'
    code_pattern = r'`[^`]+`'
    
    technical_info['code_references'].update(re.findall(function_pattern, full_text))
    technical_info['affected_components'].update(re.findall(endpoint_pattern, full_text))
    technical_info['code_references'].update(re.findall(code_pattern, full_text))
    
    return technical_info

def generate_dynamic_analysis(summary: str, description: str, technical_details: dict) -> dict:
    """Generate contextual analysis based on issue details"""
    analysis = {
        'primary_cause': '',
        'impact_areas': [],
        'technical_details': [],
        'severity_level': 'medium',
        'detailed_description': ''  # New field for detailed description
    }
    
    summary_lower = summary.lower()
    
    # Enhanced pattern matching with detailed descriptions
    if 'memory' in summary_lower:
        if 'leak' in summary_lower:
            analysis['primary_cause'] = 'Resource Management - Memory Leak'
            analysis['impact_areas'] = ['Memory Usage', 'Performance', 'Stability', 'Application Reliability']
            analysis['severity_level'] = 'high'
            
            # Generate detailed description
            affected_function = next(iter(technical_details['code_references']), 'fetchUVRulesResponse')
            affected_endpoint = next(iter(technical_details['affected_components']), '/rulehelp')
            
            analysis['detailed_description'] = f"""Memory leak detected in the {affected_function} function where response text parsing is not properly handled, leading to increased memory usage over time. The issue occurs specifically when handling large markdown responses from the {affected_endpoint} endpoint.

Key Observations:
1. Gradual increase in memory consumption during API calls
2. Memory not being released after response processing
3. Impact intensifies with larger response payloads
4. Potential garbage collection inefficiencies"""

            analysis['technical_details'] = [
                f"Affected Component: {affected_function} function in API handler",
                f"Impacted Endpoint: {affected_endpoint}",
                "Issue Pattern: Memory accumulation during response processing",
                "Root Cause: Improper resource cleanup in response handling logic"
            ]

    elif 'button' in summary_lower and ('unresponsive' in summary_lower or 'tap' in summary_lower):
        analysis['primary_cause'] = 'UI Interaction Handler Failure'
        analysis['impact_areas'] = ['User Experience', 'Mobile Interface', 'Authentication Flow']
        analysis['severity_level'] = 'high'
        
        analysis['detailed_description'] = """The login button's touch event handler on mobile devices is failing to properly register and process user interactions. This critical issue prevents users from accessing the application through the mobile interface.

Key Observations:
1. Button appears visually but doesn't respond to touch events
2. Issue specific to mobile interface
3. Other UI elements may be functioning normally
4. Potential conflict with touch event propagation"""

        analysis['technical_details'] = [
            "Component: Mobile UI Login Button",
            "Event Type: Touch/Tap Interaction",
            "Platform: Mobile Web/App Interface",
            "Impact: Critical - Blocks User Authentication"
        ]

    # Add more patterns as needed...
    
    return analysis

def generate_dynamic_solution(analysis: dict, technical_details: dict) -> str:
    """Generate solution recommendations based on analysis"""
    solutions = []
    
    if 'Memory' in analysis['primary_cause']:
        solutions.extend([
            "1. Implement proper response cleanup in finally block:",
            "   - Add explicit response.close() calls",
            "   - Implement AutoCloseable pattern for resources",
            "   - Clear parsed content after processing",
            "",
            "2. Enhance error handling for markdown parsing:",
            "   - Add proper exception handling",
            "   - Implement memory limits for parsing",
            "   - Add logging for memory usage",
            "",
            "3. Optimize response processing:",
            "   - Implement streaming for large responses",
            "   - Add memory usage monitoring",
            "   - Implement resource pooling"
        ])
    elif 'UI' in analysis['primary_cause']:
        solutions.extend([
            "1. Update touch event handling:",
            "   - Implement touchstart/touchend listeners",
            "   - Add event propagation controls",
            "   - Implement debouncing for touch events",
            "",
            "2. Enhance button implementation:",
            "   - Add visual feedback for touch states",
            "   - Implement fallback click handlers",
            "   - Add accessibility improvements",
            "",
            "3. Add comprehensive testing:",
            "   - Implement mobile device testing",
            "   - Add touch event unit tests",
            "   - Monitor touch event performance"
        ])
    
    return "\n".join(solutions)

def create_basic_rca(issue_key: str, bug_url: str, assignee_name: str, bug_summary: str, description: str = "", comments: list = None) -> dict:
    """Create dynamic RCA document from issue fields"""
    
    technical_details = analyze_technical_details(description, comments)
    analysis = generate_dynamic_analysis(bug_summary, description, technical_details)
    solution = generate_dynamic_solution(analysis, technical_details)
    
    return {
        "bug_id": issue_key,
        "bug_url": bug_url,
        "owner": assignee_name,
        "Defect Summary": bug_summary,
        "rootCause": {
            "description": analysis['detailed_description'] or analysis['primary_cause'],
            "analysis": {
                "logs": "\n".join(analysis['technical_details']),
                "impact_areas": analysis['impact_areas'],
                "severity": analysis['severity_level']
            }
        },
        "solution": solution
    }

def load_data_from_jira():
    """Load and process bug data from JIRA"""
    try:
        bugs = get_done_bugs()
        print(f"Found {len(bugs)} bugs with status 'Done'.")

        for bug in bugs:
            issue_key = bug["key"]
            bug_url = f"{os.environ['JIRA_URL']}/browse/{issue_key}"
            assignee = bug["fields"].get("assignee", {})
            assignee_name = assignee.get("displayName", "Unassigned") if assignee else "Unassigned"
            summary = bug["fields"].get("summary", "No summary available")
            description = bug["fields"].get("description", "")
            comments = bug["fields"].get("comment", {}).get("comments", [])
            attachments = bug["fields"].get("attachment", [])

            rca_processed = False
            for attachment in attachments:
                if "RCA" in attachment["filename"]:
                    process_and_store_rca(issue_key, bug_url, assignee_name, attachment)
                    rca_processed = True
                    break
            
            if not rca_processed:
                # Create and store basic RCA if none exists
                basic_rca = create_basic_rca(issue_key, bug_url, assignee_name, summary, description, comments)
                existing_document = collection.find_one({"bug_id": issue_key})
                if not existing_document:
                    collection.insert_one(basic_rca)
                    print(f"Stored basic RCA document for {issue_key} in MongoDB.")

        print("Processing complete.")
    except Exception as e:
        print(f"Error loading data from JIRA: {e}")
        raise
