import re
from typing import Dict, List, Tuple, Optional
from patterns import ISSUE_PATTERNS

class IssueAnalyzer:
    def __init__(self):
        self.patterns = ISSUE_PATTERNS

    def analyze_query(self, query: str) -> Tuple[Optional[Dict], Optional[str], Optional[str]]:
        query_lower = query.lower()
        
        for service, issues in self.patterns.items():
            for issue_type, data in issues.items():
                for pattern in data['patterns']:
                    if re.search(pattern, query_lower):
                        return data, service, issue_type
        return None, None, None

    def get_root_causes(self, query: str) -> Optional[str]:
        data, service, issue_type = self.analyze_query(query)
        if data and 'root_causes' in data:
            causes = data['root_causes']
            return f"""Root Causes for {service.title()} {issue_type.title()} Issue:

{chr(10).join(f'- {cause}' for cause in causes)}

Summary: The {service} {issue_type} issue typically occurs due to {causes[0].lower()}."""
        return None

    def get_solutions(self, query: str) -> Optional[str]:
        data, service, issue_type = self.analyze_query(query)
        if data and 'solutions' in data:
            solutions = data['solutions']
            return f"""Solutions for {service.title()} {issue_type.title()} Issue:

{chr(10).join(f'- {solution}' for solution in solutions)}

Summary: To resolve {service} {issue_type} issues, start by {solutions[0].lower()}."""
        return None
