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
from state.schemas import ContractTerms, WorkflowState

logger = logging.getLogger(__name__)


def planner_node(state: WorkflowState) -> Dict[str, Any]:
    """Planner Agent Node: Extracts structured contract terms from raw contract text using LLM structured output."""
    raw_text = state.get("raw_text", "")
    
    # Prevent hallucination on empty/short extraction
    if not raw_text or len(raw_text.strip()) < 50:
        logger.error(f"Planner node text validation failed. Extracted text length: {len(raw_text) if raw_text else 0} chars.")
        raise ValueError("PySpark failed to extract valid text from the PDF stream (extracted text length < 50 chars).")

    try:
        if not HAS_LANGCHAIN:
            raise ValueError("LangChain packages not installed")

        if settings.groq_api_key and ChatGroq:
            llm = ChatGroq(
                model=settings.groq_model,
                groq_api_key=settings.groq_api_key,
                temperature=0.0,
                max_retries=2,
            )
        elif settings.openai_api_key and ChatOpenAI:
            llm = ChatOpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                temperature=0.0,
            )
        else:
            raise ValueError("Neither GROQ_API_KEY nor OPENAI_API_KEY is configured")
        structured_llm = llm.with_structured_output(ContractTerms)

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an expert contract analyst. Extract structured contract terms from the provided contract text.\n"
                    "CRITICAL INSTRUCTIONS:\n"
                    "- Extract exact company/party names, effective dates, payment terms, and renewal terms directly from the text.\n"
                    "- Do NOT invent data. If a specific field value is not mentioned in the text, return 'Not Found'.\n"
                    "- initial_price MUST be a numeric float in USD (e.g. 150000.0, 0.0 if free/not specified). Do NOT return a string.",
                ),
                ("user", "Contract Document:\n\n{raw_text}"),
            ]
        )

        chain = prompt | structured_llm
        contract_terms: ContractTerms = chain.invoke({"raw_text": raw_text[:8000]})
        logger.info(f"Planner extracted terms successfully: {contract_terms.dict() if hasattr(contract_terms, 'dict') else contract_terms}")
        return {"contract_terms": contract_terms}

    except Exception as e:
        logger.error(f"Planner node LLM invocation error: {e}")
        raise RuntimeError(f"Planner LLM extraction failed: {str(e)}") from e
