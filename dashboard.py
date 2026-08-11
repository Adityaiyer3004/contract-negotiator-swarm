import os
import json
import requests
import streamlit as st

# Configure Streamlit Page
st.set_page_config(
    page_title="Contract Negotiator Swarm",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")

# Custom Styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.3rem;
        font-weight: 700;
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #555;
        font-size: 1.1rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        border-left: 4px solid #2a5298;
    }
    .status-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Header Section
st.markdown(
    '<div class="main-header">⚖️ Multi-Agent Contract Negotiator Swarm</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="sub-header">Autonomous PDF Contract Parsing, Counter-Offer Generation & Human-in-the-Loop Email Execution</div>',
    unsafe_allow_html=True,
)

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    backend_url = st.text_input("FastAPI Backend URL", value=FASTAPI_URL)

    st.markdown("---")
    st.subheader("🤖 Swarm Architecture")
    st.markdown(
        """
    1. **PySpark Ingestion**: PDF binary parsing
    2. **Planner Agent**: Structured extraction
    3. **Drafter Agent**: Counter-offer drafting
    4. **Reviewer Node**: Deterministic math audit (<=2% error)
    5. **Human Gate**: LangGraph `interrupt()` primitive
    6. **Execution**: Resend email API
    """
    )

    st.markdown("---")
    recipient_override = st.text_input(
        "Recipient Email Override", placeholder="stakeholder@example.com"
    )

# Session State Initialization
if "negotiation_data" not in st.session_state:
    st.session_state.negotiation_data = None
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "approval_status" not in st.session_state:
    st.session_state.approval_status = None

# Main Layout Tabs
tab_upload, tab_review = st.tabs(["📄 Upload & Ingest Contract", "🔍 Human Approval & Review"])

with tab_upload:
    st.subheader("1. Ingest Contract PDF")
    uploaded_file = st.file_uploader(
        "Choose a PDF contract file", type=["pdf"], help="Upload PDF contract document"
    )

    if uploaded_file is not None:
        st.info(f"File uploaded: **{uploaded_file.name}** ({uploaded_file.size} bytes)")

        if st.button("🚀 Start Swarm Negotiation", type="primary", use_container_width=True):
            with st.spinner("Processing contract via PySpark & LangGraph Swarm..."):
                try:
                    files = {
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            "application/pdf",
                        )
                    }
                    endpoint = f"{backend_url}/api/v1/start-negotiation/"
                    response = requests.post(endpoint, files=files, timeout=60)

                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.negotiation_data = data
                        st.session_state.thread_id = data.get("thread_id")
                        st.session_state.approval_status = "Pending Approval"
                        st.success(
                            f"Swarm paused for human approval! Thread ID: `{data.get('thread_id')}`"
                        )
                    else:
                        st.error(
                            f"API Error ({response.status_code}): {response.text}"
                        )
                except Exception as e:
                    st.error(f"Failed to communicate with FastAPI backend: {e}")
                    st.warning(
                        "Ensure the FastAPI server is running with: `uvicorn app:app --reload`"
                    )

with tab_review:
    st.subheader("2. Human-in-the-Loop Review")

    if not st.session_state.negotiation_data:
        st.info("No active negotiation thread. Please upload a contract in the Upload tab.")
    else:
        data = st.session_state.negotiation_data
        thread_id = st.session_state.thread_id
        terms = data.get("contract_terms", {})
        counter = data.get("counter_offer", {})

        st.caption(f"Active Thread ID: `{thread_id}`")

        # Column Layout for extracted terms vs proposed offer
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 📋 Extracted Contract Terms")
            st.write(f"**Party A (Vendor):** {terms.get('party_a', 'N/A')}")
            st.write(f"**Party B (Client):** {terms.get('party_b', 'N/A')}")
            st.write(f"**Effective Date:** {terms.get('effective_date', 'N/A')}")
            st.metric(
                "Initial Contract Value",
                f"${terms.get('initial_price', 0):,.2f}",
            )
            st.write(f"**Payment Terms:** {terms.get('payment_terms', 'N/A')}")
            st.write(f"**Renewal Terms:** {terms.get('renewal_terms', 'N/A')}")

            with st.expander("View Extracted Clauses"):
                for clause in terms.get("key_clauses", []):
                    st.markdown(f"- {clause}")

        with col2:
            st.markdown("### 💡 Proposed Counter-Offer")
            st.write(
                f"**Proposed Price:** `${counter.get('proposed_price', 0):,.2f}`"
            )
            st.write(
                f"**Claimed Discount:** `{counter.get('discount_percentage', 0):.2f}%`"
            )
            st.write(
                f"**Revised Payment Terms:** {counter.get('revised_payment_terms', 'N/A')}"
            )

            # Reviewer Math Validation Status Box
            math_valid = data.get("math_valid", False)
            reviewer_feedback = data.get("reviewer_feedback", "")

            if math_valid:
                st.success(f"✅ **Deterministic Math Passed**: {reviewer_feedback}")
            else:
                st.warning(f"⚠️ **Math Warning**: {reviewer_feedback}")

            st.write(f"**Business Rationale:** {counter.get('rationale', 'N/A')}")

            with st.expander("View Revised Clauses"):
                for clause in counter.get("revised_clauses", []):
                    st.markdown(f"- {clause}")

        st.markdown("---")
        st.markdown("### 🎯 Decision Gate")

        if st.session_state.approval_status != "Completed":
            btn_col1, btn_col2 = st.columns(2)

            with btn_col1:
                if st.button("✅ Approve & Dispatch Email", type="primary", use_container_width=True):
                    with st.spinner("Resuming graph execution & sending live email via Resend..."):
                        payload = {
                            "thread_id": thread_id,
                            "approved": True,
                            "recipient_email": recipient_override if recipient_override else None,
                        }
                        try:
                            endpoint = f"{backend_url}/api/v1/resume-negotiation/"
                            res = requests.post(endpoint, json=payload, timeout=30)
                            if res.status_code == 200:
                                res_data = res.json()
                                st.session_state.approval_status = "Completed"
                                st.balloons()
                                st.success("Counter-offer approved and live email dispatched!")
                                st.json(res_data.get("email_result"))
                            else:
                                st.error(f"Error resuming graph: {res.text}")
                        except Exception as e:
                            st.error(f"Failed to communicate with backend: {e}")

            with btn_col2:
                if st.button("❌ Reject Counter-Offer", type="secondary", use_container_width=True):
                    with st.spinner("Resuming graph execution with rejection state..."):
                        payload = {
                            "thread_id": thread_id,
                            "approved": False,
                        }
                        try:
                            endpoint = f"{backend_url}/api/v1/resume-negotiation/"
                            res = requests.post(endpoint, json=payload, timeout=30)
                            if res.status_code == 200:
                                st.session_state.approval_status = "Completed"
                                st.warning("Counter-offer rejected by human supervisor.")
                            else:
                                st.error(f"Error resuming graph: {res.text}")
                        except Exception as e:
                            st.error(f"Failed to communicate with backend: {e}")
        else:
            st.success("This negotiation thread has been completed.")
