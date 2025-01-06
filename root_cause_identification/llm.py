import faiss
import os
import pandas as pd
from sentence_transformers import SentenceTransformer
from together import Together
from pymongo import MongoClient

class DataBase():

    @classmethod
    def intialize(cls):
        conn = MongoClient(f"mongodb+srv://{os.environ['USER_NAME']}:{os.environ['PASSWORD']}@issues.tbatd.mongodb.net/")
        conn = conn[os.environ['DB_NAME']]
        return conn

class FAISS():
    
    def __init__(self, embed_model: SentenceTransformer, index: faiss.IndexFlatL2, data: pd.DataFrame):
        self.embed_model = embed_model
        self.index = index
        self.data = data

    @classmethod
    def initialize(cls):
        embed_model = SentenceTransformer("all-MiniLM-L6-v2")
        index  = faiss.IndexFlatL2(384)
        conn = DataBase.intialize()
        data = conn['defect_cause'].find()
        data = list(data)
        data = pd.DataFrame(data)
        return cls(embed_model, index, data)

    def add_documents(self):
        embeddings = self.embed_model.encode(self.data["defectSummary"].tolist())
        self.index.add(embeddings)
        print("document added")
        return self.embed_model, self.index, self.data
    
    @staticmethod
    def search(query, embed_model, index, data, top_k=5, threshold=0.6):
        query_embedding = embed_model.encode([query])
        distances, indices = index.search(query_embedding, top_k)
        valid_indices = [i for i, dist in zip(indices[0], distances[0]) if dist < threshold]
        if not valid_indices:
            return pd.DataFrame()
        results = data.iloc[valid_indices].copy()
        results["distance"] = distances[0][:len(valid_indices)]
        return results


class LLM():

    def __init__(self, llm: Together):
        self.llm = llm

    @classmethod
    def initialize(cls):
        llm = Together(api_key=os.environ["TOGETHER_API_KEY"])
        return cls(llm)
    
    def together(self, question, data, defect_summary):
        prompt = """
You are a highly skilled System Admin Engineer specializing in troubleshooting and root cause analysis. Your task is to analyze, diagnose, and provide a detailed root cause analysis and solutions for the defect described in the {defect_summary}.

To perform this task, you will:

1. Analyze the defect summary and correlate it with the data in {df} to identify patterns, anomalies, or the root cause of the issue.
2. Based on your analysis, respond to the user's query {user_question} by providing a detailed explanation of the root cause and step-by-step solutions to fix it.
3. Validate whether the user’s query matches any relevant defect in the dataset {df}.
		* If no match is found, respond with the following message:
		  "The query you provided is not found in the dataset. Therefore, I cannot provide a possible solution. Please check the defect summary or provide additional details."
		* If relevant data is found, provide a detailed, clear, and actionable explanation addressing the root cause and comprehensive steps to fix it.
4. If applicable, provide the contact details of the person who previously worked on the defect from the 'owner name' field in the data. If there are multiple owners, list all names. If names have already been displayed in the response, avoid repetition.

Output Requirements:

Your response must contain:

1. A detailed root cause analysis:
		* Explain the root cause of the defect in detailed numbered points, covering all relevant technical aspects to ensure a clear understanding of the issue.
2. Comprehensive solutions with detailed steps:
		* Provide step-by-step instructions to fix the root cause, ranked by effectiveness and feasibility.
		* Ensure the solution is practical and implementable, considering the system's architecture and limitations.
3. Contact escalation:
		* If the user faces doubts or roadblocks, suggest they reach out to the previous defect owner(s) for further assistance.
		* Ensure your response is structured, professional, and easy to understand, avoiding hypothetical responses.

Important: Do not generate hypothetical answers if the query is not present in the dataset.Ensure the output is in formatted plain text (not markdown).
"""

        response = self.llm.chat.completions.create(model=os.environ["MODEL"],
                    messages=[{"role": "user", "content": prompt.format(df=data, user_question=question, defect_summary=defect_summary)}])
        return response.choices[0].message.content
    
    def get_data(self, defect_summary):
        conn = DataBase.intialize()
        results = conn['defect_cause'].find({"defectSummary":defect_summary}, 
                                            {"defectSummary":1,"rootCause":1, "solution":1, "owner":1, "fixedDate":1})
        results = list(results)
        return results

    def response(self, embed_model, index, data, query):
        result = FAISS.search(query, embed_model, index, data, top_k=5)
        if result.empty:
            return "The query you provided is not found in the dataset. Therefore, I cannot provide a possible solution. Please check the defect summary or provide additional details."
        defect_summary = result.iloc[0]["defectSummary"]
        data = self.get_data(defect_summary)
        result = self.together(query, data, defect_summary)
        return result
