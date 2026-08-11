import logging
from typing import Dict, Any

try:
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import interrupt
    HAS_LANGGRAPH = True
except ImportError:
    StateGraph = None  # type: ignore
    START = "START"  # type: ignore
    END = "END"  # type: ignore
    MemorySaver = None  # type: ignore
    interrupt = None  # type: ignore
    HAS_LANGGRAPH = False


from config.settings import settings
from langchain_groq import ChatGroq

from state.schemas import WorkflowState
from agents.planner import planner_node
from agents.drafter import drafter_node
from agents.reviewer import reviewer_node

logger = logging.getLogger(__name__)

# Using Llama 3 70B for the perfect balance of blistering speed and complex reasoning
try:
    llm = ChatGroq(
        model=settings.groq_model or "llama-3.3-70b-versatile", 
        temperature=0,
        max_retries=2,
        groq_api_key=settings.groq_api_key or None,
    )
except Exception as e:
    logger.warning(f"ChatGroq initialization notice: {e}")
    llm = None


def human_approval_node(state: WorkflowState) -> Dict[str, Any]:
    """Human-in-the-Loop Node: Uses LangGraph interrupt() primitive to pause state machine

    and wait for human decision via FastAPI/Streamlit UI.
    """
    counter_offer = state.get("counter_offer")
    terms = state.get("contract_terms")

    # Call LangGraph interrupt primitive to pause graph execution
    human_response = interrupt(
        {
            "message": "Human approval required for counter-offer proposal.",
            "contract_terms": terms.dict() if hasattr(terms, "dict") else terms,
            "counter_offer": counter_offer.dict() if hasattr(counter_offer, "dict") else counter_offer,
            "reviewer_feedback": state.get("reviewer_feedback", ""),
        }
    )

    # Process response when graph is resumed
    approved = False
    if isinstance(human_response, bool):
        approved = human_response
    elif isinstance(human_response, dict):
        approved = bool(human_response.get("approved", False))

    logger.info(f"Human-in-the-Loop decision received: approved={approved}")
    return {"human_approved": approved}


def route_after_reviewer(state: WorkflowState) -> str:
    """Conditional router: Retries Drafter if math validation fails (up to 3 retries),

    otherwise routes to Human Approval node.
    """
    math_valid = state.get("math_valid", False)
    retries = state.get("math_retry_count", 0)
    MAX_RETRIES = 3

    if not math_valid and retries < MAX_RETRIES:
        logger.warning(
            f"Math check failed (Attempt {retries}/{MAX_RETRIES}). Routing back to drafter node."
        )
        return "drafter"

    logger.info("Math check passed or max retries reached. Routing to human_approval.")
    return "human_approval"


def build_contract_negotiator_graph():
    """Build and compile the LangGraph StateGraph with MemorySaver checkpointer."""
    if not HAS_LANGGRAPH:
        logger.warning("LangGraph not installed in environment. Returning None graph instance.")
        return None

    workflow = StateGraph(WorkflowState)


    # Add Nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("drafter", drafter_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("human_approval", human_approval_node)

    # Define Graph Edges
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "drafter")
    workflow.add_edge("drafter", "reviewer")

    # Conditional Routing after Reviewer
    workflow.add_conditional_edges(
        "reviewer",
        route_after_reviewer,
        {
            "drafter": "drafter",
            "human_approval": "human_approval",
        },
    )

    # Edge from Human Approval to END
    workflow.add_edge("human_approval", END)

    # Memory checkpointer for thread persistence and interrupt state saving
    checkpointer = MemorySaver()
    compiled_graph = workflow.compile(checkpointer=checkpointer)

    return compiled_graph


# Expose global graph instance
app_graph = build_contract_negotiator_graph()
