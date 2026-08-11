import logging
from typing import Dict, Any

try:
    from langchain_groq import ChatGroq
except ImportError:
    ChatGroq = None  # type: ignore

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None  # type: ignore

try:
    from langchain_core.prompts import ChatPromptTemplate
    HAS_LANGCHAIN_CORE = True
except ImportError:
    ChatPromptTemplate = None  # type: ignore
    HAS_LANGCHAIN_CORE = False

HAS_LANGCHAIN = HAS_LANGCHAIN_CORE and (ChatGroq is not None or ChatOpenAI is not None)


from config.settings import settings
from state.schemas import CounterOffer, WorkflowState

logger = logging.getLogger(__name__)


def drafter_node(state: WorkflowState) -> Dict[str, Any]:
    """Drafter Agent Node: Generates structured CounterOffer based on ContractTerms and Reviewer feedback."""
    contract_terms = state.get("contract_terms")
    reviewer_feedback = state.get("reviewer_feedback", "")
    current_retries = state.get("math_retry_count", 0)

    initial_price = contract_terms.initial_price if contract_terms else 0.0
    party_b = contract_terms.party_b if contract_terms else "Client"

    try:
        if not HAS_LANGCHAIN:
            raise ValueError("LangChain packages not installed")

        if settings.groq_api_key and ChatGroq:
            llm = ChatGroq(
                model=settings.groq_model,
                groq_api_key=settings.groq_api_key,
                temperature=0.2,
                max_retries=2,
            )
        elif settings.openai_api_key and ChatOpenAI:
            llm = ChatOpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                temperature=0.2,
            )
        else:
            raise ValueError("Neither GROQ_API_KEY nor OPENAI_API_KEY is configured")

        structured_llm = llm.with_structured_output(CounterOffer)

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a skilled corporate contract negotiator representing {party_b}.\n"
                    "Your goal is to draft a structured counter-offer.\n"
                    "If initial_price is greater than 0, propose a 10% to 20% discount on ${initial_price:,.2f}.\n"
                    "CRITICAL MATHEMATICAL RULE:\n"
                    "If initial_price > 0, proposed_price and discount_percentage MUST satisfy:\n"
                    "discount_percentage = ((initial_price - proposed_price) / initial_price) * 100\n"
                    "If initial_price is 0.0, set proposed_price to 0.0 and discount_percentage to 0.0, and focus counter-offer on payment/renewal/SLA clauses.\n\n"
                    "Previous Feedback / Reviewer Warnings:\n{feedback}",
                ),
                (
                    "user",
                    "Extracted Contract Terms:\n{terms_json}\n\nDraft the counter-offer now.",
                ),
            ]
        )

        terms_summary = (
            contract_terms.json() if hasattr(contract_terms, "json") else str(contract_terms)
        )
        chain = prompt | structured_llm

        counter_offer: CounterOffer = chain.invoke(
            {
                "party_b": party_b,
                "initial_price": initial_price,
                "feedback": reviewer_feedback or "No previous errors. Proceed with standard negotiation.",
                "terms_json": terms_summary,
            }
        )

        logger.info(
            f"Drafter generated counter-offer: {counter_offer.dict() if hasattr(counter_offer, 'dict') else counter_offer}"
        )
        return {
            "counter_offer": counter_offer,
            "math_retry_count": current_retries + 1,
        }

    except Exception as e:
        logger.error(f"Drafter node LLM invocation error: {e}")
        raise RuntimeError(f"Drafter LLM counter-offer generation failed: {str(e)}") from e
