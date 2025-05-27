from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from llm import FAISS, DataBase, LLM
from contextlib import asynccontextmanager
from pathlib import Path
import os
from dotenv import load_dotenv
import uvicorn
from pydantic import BaseModel
from jira_data_loader import load_data_from_jira
from fastapi.middleware.cors import CORSMiddleware
import signal
import markdown2
import bleach  # Add this import

defects_llm = {}
cleanup_done = False

def cleanup_resources():
    global cleanup_done
    if not cleanup_done:
        if defects_llm:
            defects_llm.clear()
        cleanup_done = True

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        BASE_DIR = Path(__file__).absolute().parent
        ENV_PATH = os.path.join(BASE_DIR, ".env")
        load_dotenv(ENV_PATH)
        load_data_from_jira()
        
        vs = FAISS.initialize()
        db = DataBase()
        faiss_data = vs.add_documents(db)
        defects_llm.update(faiss_data)
        
        yield
    except Exception as e:
        print(f"Error during startup: {e}")
        cleanup_resources()
        raise
    finally:
        cleanup_resources()

def handle_exit(signum, frame):
    cleanup_resources()
    raise KeyboardInterrupt()

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

app  = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    prompt: str
    conversation_id: str = None

VALID_DEFECT_IDS = {'SCRUM-7', 'SCRUM-8', 'SCRUM-9', 'SCRUM-11', 'SCRUM-13'}

@app.post("/defects/response")
async def defects_response(chat_request: ChatRequest):
    llm = LLM()
    query = chat_request.prompt.lower()
    db = DataBase()
    
    # Check if query mentions invalid defect IDs
    mentioned_ids = set([word.upper() for word in query.split() if word.upper().startswith('SCRUM-')])
    invalid_ids = mentioned_ids - VALID_DEFECT_IDS
    
    if invalid_ids:
        return JSONResponse(content={
            "response": {
                "message": f"""The following defect IDs are not in the current database: {', '.join(invalid_ids)}
                <br><br>Currently active defects are: {', '.join(sorted(VALID_DEFECT_IDS))}""",
                "content_type": "html"
            }
        })

    vs = FAISS.initialize()
    vs.defect_embeddings = defects_llm["index"]
    
    # Initialize relevant_defects with all defects as default
    relevant_defects = db.defect_data

    # Special handling for root cause and solution queries
    if any(keyword in query for keyword in ['root', 'cause', 'why', 'solution', 'fix', 'resolve']):
        mentioned_ids = [word.upper() for word in query.split() if word.upper().startswith('SCRUM-')]
        if mentioned_ids and mentioned_ids[0] in VALID_DEFECT_IDS:
            # Get the specific defect directly from database
            relevant_defects = [d for d in db.defect_data if d['bug_id'] == mentioned_ids[0]]
            # Add debug logging
            print(f"Found defect details: {relevant_defects[0] if relevant_defects else 'Not found'}")
    elif not any(keyword in query for keyword in ['owner', 'who', 'list', 'all defect']):
        # For specific queries that aren't about listing all defects
        relevant_indices_scores = vs.semantic_search(query, top_k=10)
        relevant_defects = db.get_defects_by_indices_with_scores(relevant_indices_scores)
        relevant_defects.sort(key=lambda x: x['relevance_score'], reverse=True)
    
    response = llm.get_response(query, relevant_defects)
    
    # Only sanitize if content type is HTML
    if response.get("content_type") == "html":
        allowed_tags = ['a', 'p', 'br', 'li', 'ul', 'ol', 'table', 'tr', 'td', 'th', 'thead', 'tbody']
        allowed_attrs = {'a': ['href', 'target']}
        response["message"] = bleach.clean(
            response["message"],
            tags=allowed_tags,
            attributes=allowed_attrs,
            protocols=['http', 'https']
        )
    
    return JSONResponse(
        content={"response": response},
        headers={"Content-Type": "application/json"}
    )

if __name__ == "__main__":
    try:
        uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
    except KeyboardInterrupt:
        cleanup_resources()