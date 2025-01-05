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
You are a highly skilled System Admin Engineer specializing in troubleshooting and resolving technical issues. Your task is to analyze and diagnose the root cause of the defect described in the {defect_summary}.

To perform this task, you will:

1. Analyze the provided defect summary and correlate it with the data in {df} to identify patterns, anomalies, or potential root causes.
2. Respond to the user's query {user_question} based on your analysis of the defect summary and data.
3. Strictly validate whether the user's query {user_question} matches any relevant defect or issue in the dataset {df}. If no match is found, respond with the following message:
   "The query you provided is not found in the dataset. Therefore, I cannot provide a possible solution. Please check the defect summary or provide additional details."
4. If relevant data is found, provide clear, actionable solutions that address the root cause, ensuring your recommendations are feasible and implementable.

Output Requirements:

1. A concise explanation of the root cause of the defect in numbered points.
2. A list of possible solutions, ranked by effectiveness and feasibility in numbered points.
3. If they have any doubts or are facing any roadblocks with the provided solution, ask them to reach out to the person who previously worked on that defect. That data can be taken from the 'owner name' field in the data. If there are multiple owners, list all the names.If the names already been displayed in response, then don't add them twice.
4. Ensure your response is structured, professional, and easy to understand.

Output: The response should be in formatted plain text and not in markdown format.
Important: Do not generate hypothetical answers for queries that are not present in the dataset.
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
