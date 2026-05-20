from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException

from database import get_declaration, init_db, store_declaration
from models import AskRequest, AskResponse, DeclarationRequest, DeclarationResponse, SummaryResponse
from rag import answer_question, init_rag
from reconcile import reconcile_with_erp


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_rag()
    yield


app = FastAPI(
    title="GreenPack EPR Compliance Service",
    description="Monthly plastic declaration, ERP reconciliation, and EPR rule Q&A.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/submit", response_model=DeclarationResponse, status_code=201)
def submit_declaration(payload: DeclarationRequest):
    """Accept GreenPack's monthly plastic declaration. No LLM — validation is deterministic."""
    return store_declaration(payload)


@app.get("/summary/{producer_id}/{month}", response_model=SummaryResponse)
def get_summary(producer_id: str, month: str):
    """Reconcile stored declaration against mock ERP feed; return structured result + LLM narrative."""
    declaration = get_declaration(producer_id, month)
    if not declaration:
        raise HTTPException(
            status_code=404,
            detail=f"No declaration found for producer '{producer_id}', month '{month}'.",
        )
    return reconcile_with_erp(declaration)


@app.post("/ask", response_model=AskResponse)
def ask_epr_question(body: AskRequest):
    """Answer plain-English questions about EPR rules via RAG over the policy corpus."""
    return answer_question(body.question)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
