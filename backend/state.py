import os
import logging
from typing import TypedDict, Literal, Optional
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt

logger = logging.getLogger(__name__)

# 1. Define the exact state schema
class ContractState(TypedDict, total=False):
    thread_id: str
    vendor_name: str
    initial_value: float
    proposed_price: float
    human_decision: Optional[Literal["APPROVE", "REJECT", "EDIT"]]


from .nodes import extraction_node, decision_gate_node, execute_email_node


# 3. Build and Compile the Graph with Postgres / Memory Fallback Checkpointer
def build_durable_graph():
    builder = StateGraph(ContractState)

    builder.add_node("extraction", extraction_node)
    builder.add_node("decision_gate", decision_gate_node)
    builder.add_node("execute_email", execute_email_node)

    builder.add_edge(START, "extraction")
    builder.add_edge("extraction", "decision_gate")

    # Conditional routing based on the human's decision
    builder.add_conditional_edges(
        "decision_gate",
        lambda state: "execute_email" if state.get("human_decision") == "APPROVE" else END,
    )
    builder.add_edge("execute_email", END)

    db_uri = os.getenv(
        "DATABASE_URL",
        "postgresql://admin:password@localhost:5432/langgraph_state",
    )

    try:
        import psycopg
        # Fast 1.5s connection check before starting connection pool
        conn = psycopg.connect(conninfo=db_uri, connect_timeout=2)
        conn.close()

        pool = ConnectionPool(conninfo=db_uri, max_size=20, kwargs={"autocommit": True})
        checkpointer = PostgresSaver(pool)
        checkpointer.setup()
        logger.info("Successfully connected to PostgreSQL durable checkpointer.")
        return builder.compile(checkpointer=checkpointer)
    except Exception as e:
        logger.warning(
            f"PostgreSQL connection unavailable ({e}). Initializing in-memory checkpointer."
        )
        checkpointer = MemorySaver()
        return builder.compile(checkpointer=checkpointer)


# Expose the compiled app
agent_app = build_durable_graph()
