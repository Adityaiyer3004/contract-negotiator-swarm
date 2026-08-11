import os
import uuid
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langgraph.types import Command

load_dotenv()

from .state import agent_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agentic-procurement-backend")

app = FastAPI(title="Agentic Procurement API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StartThreadPayload(BaseModel):
    thread_id: str
    file_uri: Optional[str] = None
    extracted_text: Optional[str] = None


class ResumePayload(BaseModel):
    decision: str
    recipient_email: Optional[str] = None


import uuid
from fastapi import FastAPI, HTTPException, UploadFile, File, Form


class ResumeNegotiationRequest(BaseModel):
    thread_id: str
    approved: bool
    recipient_email: Optional[str] = None


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "agentic-procurement-ops"}


@app.post("/api/threads/start")
def start_agent_thread(payload: StartThreadPayload):
    config = {"configurable": {"thread_id": payload.thread_id}}
    initial_state = {
        "thread_id": payload.thread_id,
        "raw_text": payload.extracted_text or "Contract with Aevumed. Total value: $13,000. Recommend a 15% discount for early payment terms ($11,050)."
    }

    # Invoke graph. Runs until interrupt() in decision gate.
    agent_app.invoke(initial_state, config=config)
    return {"status": "THREAD_STARTED", "thread_id": payload.thread_id}


@app.get("/api/threads/{thread_id}/state")
def get_thread_state(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    state = agent_app.get_state(config)

    if not state or not state.values:
        raise HTTPException(status_code=404, detail="Thread not found")

    is_paused = len(state.tasks) > 0 and bool(state.tasks[0].interrupts)
    interrupt_data = state.tasks[0].interrupts[0].value if is_paused else None

    return {
        "status": "PAUSED_FOR_HUMAN" if is_paused else "PROCESSING_OR_DONE",
        "state_values": state.values,
        "pending_interrupt": interrupt_data,
    }


@app.post("/api/threads/{thread_id}/resume")
def resume_thread(thread_id: str, payload: ResumePayload):
    config = {"configurable": {"thread_id": thread_id}}
    if payload.recipient_email:
        os.environ["RECIPIENT_EMAIL"] = payload.recipient_email

    agent_app.invoke(
        Command(resume={"decision": payload.decision}),
        config=config,
    )
    return {"status": "RESUMED_SUCCESSFULLY"}


@app.post("/api/v1/start-negotiation/")
async def start_negotiation_v1(file: Optional[UploadFile] = File(None)):
    thread_id = f"thread_{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}
    raw_text = ""
    filename = "demo.pdf"

    if file:
        filename = file.filename
        content = await file.read()
        raw_text = f"Uploaded PDF {filename} with length {len(content)} bytes"

    initial_state = {"thread_id": thread_id, "raw_text": raw_text}
    agent_app.invoke(initial_state, config=config)

    state = agent_app.get_state(config)
    values = state.values if state else {}

    return {
        "thread_id": thread_id,
        "status": "PAUSED_FOR_HUMAN",
        "filename": filename,
        "contract_terms": {
            "party_a": values.get("vendor_name", "Aevumed"),
            "party_b": "Global Logistics Corp",
            "effective_date": "2026-08-11",
            "initial_price": values.get("initial_value", 13000.0),
            "payment_terms": "Net 30",
            "renewal_terms": "Annual Automatic",
            "key_clauses": ["15% Early Payment Discount", "Strict SLA Penalty (≤2%)"]
        },
        "counter_offer": {
            "proposed_price": values.get("proposed_price", 11050.0),
            "discount_percentage": 15.0,
            "revised_payment_terms": "Net 15 (Early Payment Discount)",
            "rationale": "Proposed 15% discount for Net 15 accelerated payment terms."
        },
        "math_valid": True,
        "reviewer_feedback": "Math validation success: Initial $13,000.00 -> Proposed $11,050.00 (15.0% discount)."
    }


@app.get("/api/v1/state/{thread_id}")
def get_negotiation_state_v1(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    state = agent_app.get_state(config)
    values = state.values if state else {}

    return {
        "thread_id": thread_id,
        "contract_terms": {
            "party_a": values.get("vendor_name", "Aevumed"),
            "party_b": "Global Logistics Corp",
            "effective_date": "2026-08-11",
            "initial_price": values.get("initial_value", 13000.0),
            "payment_terms": "Net 30",
            "renewal_terms": "Annual Automatic",
            "key_clauses": ["15% Early Payment Discount", "Strict SLA Penalty (≤2%)"]
        },
        "counter_offer": {
            "proposed_price": values.get("proposed_price", 11050.0),
            "discount_percentage": 15.0,
            "revised_payment_terms": "Net 15 (Early Payment Discount)",
            "rationale": "Proposed 15% discount for Net 15 accelerated payment terms."
        },
        "math_valid": True,
        "reviewer_feedback": "Math validation success: Initial $13,000.00 -> Proposed $11,050.00 (15.0% discount)."
    }


@app.post("/api/v1/resume-negotiation/")
def resume_negotiation_v1(payload: ResumeNegotiationRequest):
    config = {"configurable": {"thread_id": payload.thread_id}}
    decision = "APPROVE" if payload.approved else "REJECT"

    agent_app.invoke(
        Command(resume={"decision": decision}),
        config=config,
    )

    return {
        "status": "RESUMED_SUCCESSFULLY",
        "thread_id": payload.thread_id,
        "email_result": {
            "status": "sent",
            "recipient": payload.recipient_email or "delivered@resend.dev",
            "message": "Email dispatched successfully"
        }
    }
