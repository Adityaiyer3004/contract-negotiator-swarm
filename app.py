import uuid
import logging
from typing import Optional, Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from langgraph.types import Command

from ingestion.spark_parser import parse_pdf_contract_spark, ingestor
from graph.workflow import app_graph
from execution.dispatcher import dispatch_counter_offer_email

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Multi-Agent Contract Negotiator Swarm API",
    version="1.0.0",
    description="FastAPI gateway exposing LangGraph contract negotiation workflow with Human-in-the-Loop approval.",
)

# Enable CORS for Streamlit frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResumeNegotiationRequest(BaseModel):
    thread_id: str = Field(description="Unique LangGraph thread ID")
    approved: bool = Field(
        description="True to approve counter-offer and dispatch email, False to reject"
    )
    recipient_email: Optional[str] = Field(
        default=None, description="Optional override recipient email address"
    )


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "Contract Negotiator Swarm Gateway"}


@app.post("/api/v1/start-negotiation/")
async def start_negotiation(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Ingest PDF contract straight from Streamlit UI into PySpark in-memory,

    initialize LangGraph swarm, and pause execution at Human Approval node.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        # 1. Read bytes directly into memory (no saving to disk!)
        pdf_bytes = await file.read()
        logger.info(f"Streaming contract PDF '{file.filename}' ({len(pdf_bytes)} bytes) to PySpark in-memory")

        # 2. Pass bytes directly to PySpark
        raw_text = ingestor.process_pdf_bytes(pdf_bytes)
        text_len = len(raw_text) if raw_text else 0
        logger.info(f"PySpark extracted raw_text length: {text_len} chars")
        print(f"[DEBUG] PySpark extracted raw_text length: {text_len} chars")

        if not raw_text or text_len < 50:
            raise HTTPException(
                status_code=400, detail=f"Could not parse valid text from PDF (length: {text_len} chars)"
            )

        # 3. State Machine Layer: Initialize graph with unique thread ID
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = {
            "raw_text": raw_text,
            "math_retry_count": 0,
        }

        # Stream graph execution until interrupt
        for event in app_graph.stream(initial_state, config):
            pass

        # Fetch state snapshot at interrupt
        state_snapshot = app_graph.get_state(config)
        state_values = state_snapshot.values if state_snapshot else {}

        terms = state_values.get("contract_terms")
        counter_offer = state_values.get("counter_offer")

        terms_dict = terms.dict() if hasattr(terms, "dict") else terms
        counter_offer_dict = (
            counter_offer.dict() if hasattr(counter_offer, "dict") else counter_offer
        )

        next_steps = state_snapshot.next if state_snapshot else ()
        status = "PAUSED_FOR_HUMAN_APPROVAL" if "human_approval" in next_steps else "COMPLETED"

        pending_review = (
            state_snapshot.tasks[0].interrupts[0].value
            if state_snapshot and state_snapshot.tasks and state_snapshot.tasks[0].interrupts
            else None
        )

        return {
            "thread_id": thread_id,
            "status": status,
            "filename": file.filename,
            "contract_terms": terms_dict,
            "counter_offer": counter_offer_dict,
            "math_valid": state_values.get("math_valid", False),
            "reviewer_feedback": state_values.get("reviewer_feedback", ""),
            "pending_review": pending_review,
        }

    except Exception as e:
        logger.error(f"Error in start_negotiation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to process negotiation: {str(e)}"
        )


@app.post("/api/v1/resume-negotiation/")
async def resume_negotiation(req: ResumeNegotiationRequest) -> Dict[str, Any]:
    """Resume a paused LangGraph negotiation thread with human approval decision.

    Triggers live email dispatch if approved.
    """
    config = {"configurable": {"thread_id": req.thread_id}}

    try:
        # Check current state snapshot
        snapshot = app_graph.get_state(config)
        if not snapshot or not snapshot.next:
            raise HTTPException(
                status_code=404,
                detail=f"Thread '{req.thread_id}' is either invalid or already completed.",
            )

        # Resume LangGraph thread with human decision payload via Command
        app_graph.invoke(Command(resume={"approved": req.approved}), config)

        # Retrieve updated state snapshot
        updated_snapshot = app_graph.get_state(config)
        state_values = updated_snapshot.values if updated_snapshot else {}

        contract_terms = state_values.get("contract_terms")
        counter_offer = state_values.get("counter_offer")

        email_result = None
        if req.approved:
            # Step 4 Execution Layer: Dispatch email upon human approval
            email_result = dispatch_counter_offer_email(
                contract_terms=contract_terms,
                counter_offer=counter_offer,
                recipient_email=req.recipient_email,
            )

        return {
            "thread_id": req.thread_id,
            "approved": req.approved,
            "status": "approved_and_dispatched" if req.approved else "rejected_by_human",
            "email_result": email_result,
        }

    except Exception as e:
        logger.error(f"Error in resume_negotiation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to resume negotiation: {str(e)}"
        )


@app.get("/api/v1/state/{thread_id}")
async def get_state(thread_id: str) -> Dict[str, Any]:
    """Inspect state snapshot of an active thread ID."""
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = app_graph.get_state(config)

    if not snapshot:
        raise HTTPException(status_code=404, detail="Thread state not found.")

    state_values = snapshot.values
    terms = state_values.get("contract_terms")
    counter = state_values.get("counter_offer")

    return {
        "thread_id": thread_id,
        "next_nodes": list(snapshot.next),
        "contract_terms": terms.dict() if hasattr(terms, "dict") else terms,
        "counter_offer": counter.dict() if hasattr(counter, "dict") else counter,
        "math_valid": state_values.get("math_valid", False),
        "human_approved": state_values.get("human_approved"),
    }
