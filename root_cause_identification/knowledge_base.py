ISSUE_KNOWLEDGE_BASE = {
    "kafka_duplicates": {
        "patterns": ["duplicate message", "message duplication", "duplicate kafka"],
        "category": "kafka_messaging",
        "root_causes": [
            "Consumer group rebalancing causing message reprocessing",
            "Multiple consumer instances with same group.id",
            "Network issues causing offset commit failures",
            "Manual offset reset or incorrect offset management",
            "Producer retries due to network issues",
            "Incorrect idempotence configuration"
        ],
        "solutions": [
            "Implement idempotent processing using unique message IDs",
            "Configure proper consumer group IDs",
            "Enable producer idempotence",
            "Implement deduplication logic",
            "Monitor and handle consumer group rebalancing properly"
        ]
    },
    "policy_missing": {
        "patterns": ["missing policy", "policy not found", "policy details missing"],
        "category": "policy_service",
        "root_causes": [
            "Race condition between policy update and Kafka producer",
            "MongoDB document update not committed",
            "Missing field mapping in payload",
            "Asynchronous update timing issues"
        ],
        "solutions": [
            "Implement retry mechanism for policy fetching",
            "Add validation for required policy fields",
            "Ensure database updates are committed before sending",
            "Add proper field mapping configuration"
        ]
    }
}

class PatternAnalyzer:
    def __init__(self):
        self.patterns = {}
        self.learned_patterns = {}
    
    def learn_from_defects(self, defects):
        """Learn patterns from existing defect data"""
        for defect in defects:
            summary = defect.get('Defect Summary', '').lower()
            root_cause = defect.get('rootCause', {})
            if isinstance(root_cause, dict):
                root_cause = root_cause.get('description', '')
            
            # Extract key phrases from summary
            key_phrases = self._extract_key_phrases(summary)
            
            # Add to learned patterns
            for phrase in key_phrases:
                if phrase not in self.learned_patterns:
                    self.learned_patterns[phrase] = {
                        'count': 0,
                        'root_causes': set(),
                        'solutions': set()
                    }
                self.learned_patterns[phrase]['count'] += 1
                if root_cause:
                    self.learned_patterns[phrase]['root_causes'].add(root_cause)
                if defect.get('solution'):
                    self.learned_patterns[phrase]['solutions'].add(defect['solution'])
    
    def _extract_key_phrases(self, text):
        """Extract potential key phrases from text"""
        # Simple phrase extraction - can be enhanced with NLP
        words = text.lower().split()
        phrases = []
        for i in range(len(words)):
            if i > 0:
                phrases.append(f"{words[i-1]} {words[i]}")
            if i > 1:
                phrases.append(f"{words[i-2]} {words[i-1]} {words[i]}")
        return phrases
    
    def match_pattern(self, query):
        """Match query against known and learned patterns"""
        matches = []
        
        # Check predefined patterns
        for issue_type, data in ISSUE_KNOWLEDGE_BASE.items():
            for pattern in data['patterns']:
                if pattern in query.lower():
                    matches.append({
                        'type': 'predefined',
                        'category': data['category'],
                        'data': data
                    })
        
        # Check learned patterns
        for phrase, data in self.learned_patterns.items():
            if phrase in query.lower() and data['count'] >= 2:  # Threshold for learned patterns
                matches.append({
                    'type': 'learned',
                    'category': 'dynamic',
                    'data': {
                        'root_causes': list(data['root_causes']),
                        'solutions': list(data['solutions'])
                    }
                })
        
        return matches
