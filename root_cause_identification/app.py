from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from llm import FAISS, DataBase, LLM
from contextlib import asynccontextmanager
from pathlib import Path
import os
from dotenv import load_dotenv
import uvicorn
from pydantic import BaseModel
from jira_data_loader import load_data_from_jira
from fastapi.middleware.cors import CORSMiddleware

defects_llm = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    BASE_DIR = Path(__file__).absolute().parent
    ENV_PATH = os.path.join(BASE_DIR, ".env")
    load_dotenv(ENV_PATH)
    load_data_from_jira()
    vs = FAISS.initialize()
    defects_llm["embed_model"], defects_llm["index"], defects_llm["data"] = vs.add_documents()
    yield
    defects_llm.clear()

app  = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)


@app.post("/defects/response")
async def defects_response(request: Request):
    data = await request.json()
    llm = LLM.initialize()
    response = llm.response(defects_llm["embed_model"], defects_llm["index"], defects_llm["data"], data['prompt'])
    datawe = JSONResponse(content={"response": response})
    print(response)
    return JSONResponse(content={"response": response})

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)