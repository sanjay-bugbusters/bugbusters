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
        self.data["Defect Summary"] = self.data["Defect Summary"].apply(lambda x: str(x) if not isinstance(x, str) else x)
        embeddings = self.embed_model.encode(self.data["Defect Summary"].tolist())
        self.index.add(embeddings)
        print("document added")
        return self.embed_model, self.index, self.data
    
    @staticmethod
    def search(query, embed_model, index, data, top_k=5, threshold=0.8):
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

Response Requirements:

Your response must include the following:

1. Start with a summary of the defect. Do not include the bug ID or bug URL in this section.
2. Provide a detailed explanation of the root cause. Use numbered points to ensure clarity and comprehensiveness.
3. Suggest step-by-step solutions to resolve the issue. Ensure the steps are ranked by effectiveness and practicality, considering the system's architecture and limitations.
4. Include the JIRA ID and JIRA URL at the end of your response in a dedicated section. Explain the importance of the JIRA ID (e.g., for tracking and referencing purposes) and provide the JIRA URL as a clickable hyperlink.
5. If the user faces doubts or roadblocks, suggest they reach out to the previous defect owner(s) for further assistance.
6. Structure your response in plain text, ensuring clarity and professionalism without explicitly stating section headings like "Root Cause Analysis" or "Comprehensive Solutions."
7. Provide a disclaimer at the end stating the response provided is based solely on the available dataset and is intended to offer guidance. It may not precisely correspond to the specific defect being investigated. Users are advised to validate the information provided and conduct further research for an accurate and comprehensive resolution.

Important: Avoid hypothetical answers if the query is not found in the dataset. Always ensure the response is formatted as plain text (not markdown) for better readability.
"""


        response = self.llm.chat.completions.create(model=os.environ["MODEL"],
                    messages=[{"role": "user", "content": prompt.format(df=data, user_question=question, defect_summary=defect_summary)}])
        return response.choices[0].message.content
    
    def get_data(self, defect_summary):
        conn = DataBase.intialize()
        results = conn['defect_cause'].find({"Defect Summary":defect_summary}, 
                                            {"Defect Summary":1,"rootCause":1, "solution":1, "owner":1, "bug_id":1, "bug_url":1})
        results = list(results)
        return results

    def response(self, embed_model, index, data, query):
        search_results = FAISS.search(query, embed_model, index, data, top_k=5, threshold=0.8)
    
        if search_results.empty:
            return {
                "message": "The query you provided is not found in the dataset. Therefore, I cannot provide a possible solution. Please check the defect summary or provide additional details.",
                "results": []
            }

        results_with_analysis = []
        defect_summary = search_results.iloc[0]["Defect Summary"]
        data = self.get_data(defect_summary)
        analysis = self.together(query, data, defect_summary)
        threshold = 0.8
        relevance_percentage = round((1 - search_results["distance"].iloc[0] / threshold) * 100 if isinstance(search_results["distance"], pd.Series) else (1 - search_results["distance"] / threshold) * 100)
        results_with_analysis.append({
            "defectSummary": defect_summary,
            "relevance": relevance_percentage,
            "analysis": analysis
        })
        

        return {
            "message": "Relevant defects found.",
            "results": results_with_analysis
    }

