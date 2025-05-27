import faiss
import os
import pandas as pd
import re
import random
from sentence_transformers import SentenceTransformer
from together import Together
from pymongo import MongoClient
import uuid
from datetime import datetime, timedelta
from difflib import get_close_matches

class DataBase:

    @classmethod
    def initialize(cls):
        try:
            # Ensure environment variables are set
            user_name = os.environ.get('USER_NAME')
            password = os.environ.get('PASSWORD')
            db_name = os.environ.get('DB_NAME')

            if not user_name or not password or not db_name:
                raise ValueError("Missing required environment variables: USER_NAME, PASSWORD, or DB_NAME")

            # Establish MongoDB connection
            conn = MongoClient(f"mongodb+srv://{user_name}:{password}@pocapp.aegpzjw.mongodb.net/")
            db = conn[db_name]
            return db
        except Exception as e:
            raise ConnectionError(f"Failed to connect to the database: {e}")

class FAISS:

    def __init__(self, embed_model: SentenceTransformer, index: faiss.IndexFlatL2, data: pd.DataFrame):
        self.embed_model = embed_model
        self.index = index
        self.data = data

    @classmethod
    def initialize(cls):
        embed_model = SentenceTransformer("all-MiniLM-L6-v2")
        index = faiss.IndexFlatL2(384)
        conn = DataBase.initialize()
        data = list(conn['defect_cause'].find())
        df = pd.DataFrame(data)
        return cls(embed_model, index, df)

    def add_documents(self):
        self.data["Defect Summary"] = self.data["Defect Summary"].astype(str)
        embeddings = self.embed_model.encode(self.data["Defect Summary"].tolist())
        self.index.add(embeddings)
        print("Documents added to FAISS index")
        return self.embed_model, self.index, self.data

    @staticmethod
    def search(query, embed_model, index, data, top_k=5, threshold=0.8):
        # Extract bug ID from query text
        bug_id_pattern = re.search(r'[A-Z]+-\d+', query.upper())
        # Enhanced owner name patterns to handle more variations
        owner_patterns = [
            r'(?:which|what|show|list|get)\s+(?:are|is)\s+(?:the\s+)?(?:defects?|bugs?|issues?)?\s*(?:by|of|for|owned\s+by)?\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)',  # "which are the bugs by Nishanth"
            r'(?:defect\s+)?([A-Za-z]+(?:\s+[A-ZaZ]+)?)\s+(?:is|has)\s+created',  # existing pattern
            r'(?:owner|created by|by)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)',  # "owner Nishanth" or "created by Nishanth"
            r'([A-Za-z]+(?:\s+[A-Za-z]+)?)\s*(?:\'s)?\s*(?:defects?|bugs?)',  # "Nishanth's bugs"
            r'^([A-Za-z]+(?:\s+[A-Za-z]+)?)$'  # Just the name
        ]

        # Check for direct bug ID match first
        if bug_id_pattern:
            bug_id = bug_id_pattern.group()
            direct_match = data[data['bug_id'] == bug_id]
            if not direct_match.empty:
                direct_match["distance"] = 0.0
                print(f"Found direct bug ID match for {bug_id}")
                return direct_match
            print(f"No direct match found for bug ID {bug_id}")

        # Enhanced owner name matching with caching
        owner_name = None
        for pattern in owner_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                owner_name = match.group(1).strip()
                break

        # Check for owner match with improved name handling
        if owner_name:
            print(f"Searching for defects by owner: {owner_name}")
            
            # Try exact match first (case insensitive)
            owner_match = data[data['owner'].str.lower() == owner_name.lower()]
            
            # If no exact match, try partial match
            if owner_match.empty:
                owner_match = data[data['owner'].str.lower().str.contains(owner_name.lower(), na=False)]
            
            if not owner_match.empty:
                owner_match = owner_match.sort_values('bug_id', ascending=False).head(top_k)
                owner_match["distance"] = 0.0
                print(f"Found {len(owner_match)} defects for owner {owner_name}")
                return owner_match
            print(f"No defects found for owner {owner_name}")

        # Continue with semantic search if no direct matches
        query = query.lower().strip()
        query_keywords = query.split()
        
        # Optimize context based on search type
        if bug_id_pattern:
            threshold = 0.9
            query = f"{query} defect issue"
        elif owner_name:  # Changed from owner_patterns to owner_name
            threshold = 0.9
            query = f"defects by {owner_name}"  # Simplified query context
        elif len(query_keywords) < 3:
            query = " ".join(query_keywords + ["defect", "bug"])

        query_embedding = embed_model.encode([query])
        distances, indices = index.search(query_embedding, top_k)
        
        # More permissive threshold for bug ID and owner searches
        search_threshold = threshold + 0.2 if (bug_id_pattern or owner_patterns) else threshold + 0.1
        valid_indices = [i for i, dist in zip(indices[0], distances[0]) if dist < search_threshold]
        
        if not valid_indices:
            return pd.DataFrame()

        results = data.iloc[valid_indices].copy()
        results["distance"] = distances[0][:len(valid_indices)]
        return results


class LLM:
    def __init__(self, llm: Together):
        self.llm = llm
        self.greeting_patterns = {
            r'\b(hi|hello|hey|greetings|howdy)\b': [
                "Hello! I'm Bugbuster, your defect resolution assistant. How can I help you today?",
                "Hi there! I'm here to help with any technical issues. What problem would you like me to solve?",
                "Hello! I'm ready to assist with troubleshooting. Could you describe the issue you're facing?"
            ],
            r'\b(good morning|morning)\b': [
                "Good morning! I'm Bugbuster, ready to help with any technical issues today."
            ],
            r'\b(good afternoon|afternoon)\b': [
                "Good afternoon! How can I assist with your technical queries today?"
            ],
            r'\b(good evening|evening)\b': [
                "Good evening! I'm here to help resolve any defects or issues you're encountering."
            ],
            r'\b(how are you|how\'s it going|how do you do|how are things)\b': [
                "I'm functioning well and ready to assist with any technical issues. How can I help you today?",
                "I'm operational and ready to help! What defect or issue would you like assistance with?"
            ],
            r'\b(thanks|thank you|thx|ty)\b': [
                "You're welcome! Let me know if you need any more help with technical issues.",
                "Happy to help! Feel free to ask if you have any more questions about defects or troubleshooting."
            ],
            r'\b(bye|goodbye|see you|farewell)\b': [
                "Goodbye! Feel free to return whenever you need assistance with defects or technical issues.",
                "Until next time! I'll be here when you need technical support."
            ]
        }
        self.fallback_response = "I'm designed to help with technical issues and defect resolution. Could you please describe the problem you're experiencing?"
        self.conversations = {}  # Store conversation history
        self.context_window = timedelta(minutes=30)  # Context window for conversations

    def _cleanup_old_conversations(self):
        current_time = datetime.now()
        expired = [conv_id for conv_id, conv in self.conversations.items() 
                  if (current_time - conv['last_updated']) > self.context_window]
        for conv_id in expired:
            del self.conversations[conv_id]

    def get_or_create_conversation(self, conversation_id=None):
        self._cleanup_old_conversations()
        if not conversation_id or conversation_id not in self.conversations:
            conversation_id = str(uuid.uuid4())
            self.conversations[conversation_id] = {
                'history': [],
                'last_updated': datetime.now(),
                'context': {}
            }
        return conversation_id

    def is_greeting(self, text):
        """Detect if the input is a conversational greeting and return appropriate response"""
        text = text.lower().strip()

        # Optional Enhancement: If it's a bug ID like SCRUM-13, treat it as NOT a greeting
        if re.match(r'^[A-Z]+-\d+$', text.strip(), re.IGNORECASE):
            return False, None

        # Only match if actual greeting keywords are present
        for pattern, responses in self.greeting_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return True, random.choice(responses)

        # Otherwise, it's not a greeting
        return False, None

    @classmethod
    def initialize(cls):
        try:
            llm = Together(api_key=os.environ["TOGETHER_API_KEY"])
            return cls(llm)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize LLM: {e}")

    def generate_analysis(self, question, defect_data, defect_summary, conversation_id=None):
        conv_id = self.get_or_create_conversation(conversation_id)
        conversation = self.conversations[conv_id]
        conversation['last_updated'] = datetime.now()

        # Add context from conversation history
        context = ""
        if conversation['history']:
            context = "\nPrevious conversation:\n" + "\n".join(
                [f"User: {h['user']}\nAssistant: {h['assistant']}" 
                 for h in conversation['history'][-3:]]  # Last 3 exchanges
            )

        # Format bug details with correct owner and clickable link
        if defect_data:
            bug_details = f"""Bug Details:
- ID: {defect_data.get('bug_id', 'N/A')}
- Summary: {defect_data.get('Defect Summary', 'N/A')}
- Root Cause: {defect_data.get('rootCause', {}).get('description', 'N/A')}
- Solution: {defect_data.get('solution', 'N/A')}
- Owner: {defect_data.get('owner', 'N/A')}
- Link: <a href="{defect_data.get('bug_url', '#')}" target="_blank">Click here</a>"""
        else:
            bug_details = "Bug details not found."

        prompt = f"""
You are Bugbuster. Respond with only the provided bug details, no additional context or questions.

{bug_details}
"""
        response = self.llm.chat.completions.create(
            model=os.environ["MODEL"],
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Update conversation history
        conversation['history'].append({
            'user': question,
            'assistant': response.choices[0].message.content,
            'timestamp': datetime.now()
        })
        
        return response.choices[0].message.content, conv_id

    def get_defect_data(self, defect_summary):
        conn = DataBase.initialize()
        # Try to find by bug_id first if it matches the pattern
        if re.match(r'^[A-Z]+-\d+$', defect_summary.strip(), re.IGNORECASE):
            bug_id = defect_summary.upper()
            result = conn['defect_cause'].find_one(
                {"bug_id": bug_id},
                {"Defect Summary":1, "rootCause":1, "solution":1, "owner":1, "bug_id":1, "bug_url":1}
            )
            if result:
                print(f"Found defect data for bug ID: {bug_id}")
                return result

        # Fall back to defect summary search
        result = conn['defect_cause'].find_one(
            {"Defect Summary": defect_summary},
            {"Defect Summary":1, "rootCause":1, "solution":1, "owner":1, "bug_id":1, "bug_url":1}
        )
        return result

    def normalize_text(self, text):
        """Normalize text by handling misspellings and variations"""
        # Remove special characters except dots
        text = re.sub(r'[^a-zA-Z0-9\s\.]', '', text)
        # Common misspelling replacements
        replacements = {
            'incorrekt': 'incorrect',
            'maping': 'mapping',
            'profle': 'profile',
            'servise': 'service',
            'misng': 'missing',
            'detals': 'details',
            'respons': 'response',
            'servic': 'service'
        }
        
        text = text.lower()
        for wrong, right in replacements.items():
            text = text.replace(wrong, right)
        
        # Handle period at the end
        text = text.rstrip('.')
        return ' '.join(text.split())

    def find_best_match(self, defect_title, data):
        """Find best matching defect using improved fuzzy matching"""
        normalized_title = self.normalize_text(defect_title)
        
        # First try exact match after normalization
        for _, row in data.iterrows():
            if self.normalize_text(row['Defect Summary']) == normalized_title:
                return pd.DataFrame([row])
        
        # If no exact match, try fuzzy matching
        defect_summaries = data['Defect Summary'].apply(self.normalize_text).tolist()
        matches = get_close_matches(normalized_title, defect_summaries, n=3, cutoff=0.6)
        
        if matches:
            potential_matches = []
            for match in matches:
                matching_idx = data['Defect Summary'].apply(
                    lambda x: self.normalize_text(x) == match
                )
                if any(matching_idx):
                    potential_matches.append(data[matching_idx].iloc[0])
            
            if potential_matches:
                return pd.DataFrame(potential_matches)
        
        # Try partial matching if still no results
        words = set(normalized_title.split())
        for _, row in data.iterrows():
            row_words = set(self.normalize_text(row['Defect Summary']).split())
            if len(words & row_words) / len(words) >= 0.7:  # 70% word match
                return pd.DataFrame([row])
                
        return pd.DataFrame()

    def response(self, embed_model, index, data, query, conversation_id=None):
        print(f"Processing query: {query}")
        
        is_greeting, greeting_response = self.is_greeting(query)
        if is_greeting:
            return {"message": greeting_response, "results": []}

        # Enhanced bug query patterns
        bug_query_patterns = [
            r'(?:show|get|find)\s+(?:me\s+)?(?:all\s+)?bugs?\s+(?:by|for|owned\s+by)\s+(.+?)(?:\?|$)',
            r'(?:what|which)\s+(?:are|is)\s+(?:the\s+)?(?:bugs?|defects?)\s+(?:owned\s+by|of)\s+(.+?)(?:\?|$)',
            r'(.+?)(?:\'s)\s+(?:bugs?|defects?)(?:\?|$)'
        ]

        # Check for bug query
        for pattern in bug_query_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                owner_name = match.group(1).strip()
                matching_defects = data[data['owner'].str.contains(owner_name, case=False, na=False)]
                
                if not matching_defects.empty:
                    bug_list = matching_defects.apply(
                        lambda x: f"• {x['bug_id']}: {x['Defect Summary']}", 
                        axis=1
                    ).tolist()
                    return {
                        "message": f"Bugs owned by {owner_name}:\n" + "\n".join(bug_list),
                        "results": []
                    }
                return {
                    "message": f"No bugs found for owner: {owner_name}",
                    "results": []
                }

        # Enhanced root cause query patterns
        root_cause_patterns = [
            r'(?:what|tell|show)\s+(?:is|are)\s+(?:the\s+)?root\s*(?:cause|reason)\s+(?:of|for)\s+(.+?)(?:\?|$)',
            r'why\s+did\s+(.+?)\s+(?:happen|occur|fail)(?:\?|$)',
            r'what\s+caused\s+(.+?)(?:\?|$)'
        ]

        # Check for root cause query without requiring quotes
        for pattern in root_cause_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                defect_title = match.group(1).strip().strip('"\'')
                print(f"Searching for root cause of: {defect_title}")
                matching_defect = self.find_best_match(defect_title, data)
                
                if not matching_defect.empty:
                    defect_data = self.get_defect_data(matching_defect.iloc[0]['Defect Summary'])
                    root_cause = defect_data.get('rootCause', {}).get('description', 'Root cause not found')
                    return {
                        "message": f"Root Cause: {root_cause}",
                        "results": []
                    }
                break

        # Enhanced owner query patterns
        owner_query_patterns = [
            r'(?:who|what|tell|show)\s+(?:is|are)\s+(?:the\s+)?owner\s+of\s+(.+?)(?:\?|$)',
            r'who\s+owns\s+(.+?)(?:\?|$)',
            r'tell\s+me\s+(?:the\s+)?owner\s+of\s+(.+?)(?:\?|$)'
        ]

        # Check for owner query without requiring quotes
        for pattern in owner_query_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                defect_title = match.group(1).strip().strip('"\'')
                print(f"Searching for owner of: {defect_title}")
                matching_defect = self.find_best_match(defect_title, data)
                
                if not matching_defect.empty:
                    owner = matching_defect.iloc[0].get('owner', 'Owner not found')
                    original_summary = matching_defect.iloc[0]['Defect Summary']
                    return {
                        "message": f"The owner of '{original_summary}' is: {owner}",
                        "results": []
                    }
                break

        # Enhanced solution query patterns
        solution_patterns = [
            r'(?:what|tell|show)\s+(?:is|are|was)\s+(?:the\s+)?solution(?:s)?\s+(?:for|to|of)\s+(.+?)(?:\?|$)',
            r'how\s+(?:was|were)\s+(.+?)\s+(?:fixed|resolved|solved)(?:\?|$)',
            r'how\s+(?:to|do\s+(?:you|we|i))?\s+(?:fix|solve|resolve)\s+(.+?)(?:\?|$)'
        ]

        # Check for solution query
        for pattern in solution_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                defect_title = match.group(1).strip().strip('"\'')
                print(f"Searching for solution of: {defect_title}")
                matching_defect = self.find_best_match(defect_title, data)
                
                if not matching_defect.empty:
                    defect_data = self.get_defect_data(matching_defect.iloc[0]['Defect Summary'])
                    solution = defect_data.get('solution', 'Solution not found')
                    return {
                        "message": f"Solution: {solution}",
                        "results": []
                    }
                break

        # Continue with regular search if no direct match
        search_results = FAISS.search(query, embed_model, index, data, top_k=5, threshold=0.8)
        
        if search_results.empty:
            return {
                "message": "The query you provided is not found in the dataset. Please try with more specific keywords.",
                "results": []
            }

        # For regular search, update message
        results_with_analysis = []
        for _, row in search_results.iterrows():
            defect_summary = row["Defect Summary"]
            defect_data = self.get_defect_data(defect_summary)
            analysis, conv_id = self.generate_analysis(query, defect_data, defect_summary, conversation_id)
            relevance_percentage = round((1 - row["distance"] / 0.8) * 100)
            results_with_analysis.append({
                "defectSummary": defect_summary,
                "relevance": relevance_percentage,
                "analysis": analysis
            })

        return {
            "message": f"Found relevant defect information:",
            "results": results_with_analysis,
            "conversation_id": conv_id
        }
