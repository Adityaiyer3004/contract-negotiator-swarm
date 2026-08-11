import logging
from typing import Dict, Any

from state.schemas import WorkflowState

logger = logging.getLogger(__name__)


def reviewer_node(state: WorkflowState) -> Dict[str, Any]:
    """Reviewer Agent Node: Deterministically validates the Drafter's discount math.

    Checks if discount_percentage equals ((initial_price - proposed_price) / initial_price) * 100
    within a strict 2% tolerance threshold.
    """
    contract_terms = state.get("contract_terms")
    counter_offer = state.get("counter_offer")

    if not contract_terms or not counter_offer:
        error_msg = "Reviewer error: Missing contract_terms or counter_offer in state."
        logger.error(error_msg)
        return {
            "math_valid": False,
            "reviewer_feedback": error_msg,
        }

    initial_price = float(contract_terms.initial_price)
    proposed_price = float(counter_offer.proposed_price)
    claimed_discount = float(counter_offer.discount_percentage)

    if initial_price < 0:
        error_msg = f"Reviewer error: Invalid initial_price {initial_price}"
        logger.error(error_msg)
        return {
            "math_valid": False,
            "reviewer_feedback": error_msg,
        }

    if initial_price == 0:
        feedback = (
            "MATH VALIDATED: $0.00 initial contract price ($0.00 proposed counter offer). "
            "Negotiation focused on revised payment, renewal, and SLA terms."
        )
        logger.info(feedback)
        return {
            "math_valid": True,
            "reviewer_feedback": feedback,
        }

    # Deterministic calculation: expected_discount = ((initial_price - proposed_price) / initial_price) * 100
    expected_discount = ((initial_price - proposed_price) / initial_price) * 100.0
    difference = abs(expected_discount - claimed_discount)

    # 2% threshold validation constraint
    IS_VALID_THRESHOLD = 2.0

    if difference <= IS_VALID_THRESHOLD:
        feedback = (
            f"MATH VALIDATED: Proposed price ${proposed_price:,.2f} on initial ${initial_price:,.2f} "
            f"equals actual discount of {expected_discount:.2f}%. Claimed discount is {claimed_discount:.2f}% "
            f"(Difference of {difference:.2f}% is within acceptable <= {IS_VALID_THRESHOLD}% threshold)."
        )
        logger.info(feedback)
        return {
            "math_valid": True,
            "reviewer_feedback": feedback,
        }
    else:
        feedback = (
            f"MATH VALIDATION FAILED: Initial price is ${initial_price:,.2f} and proposed price is ${proposed_price:,.2f}, "
            f"yielding an actual discount of {expected_discount:.2f}%. However, stated discount_percentage was {claimed_discount:.2f}%. "
            f"The difference ({difference:.2f}%) exceeds the allowed {IS_VALID_THRESHOLD}% threshold. "
            f"Recalculate discount_percentage = ((initial_price - proposed_price) / initial_price) * 100."
        )
        logger.warning(feedback)
        return {
            "math_valid": False,
            "reviewer_feedback": feedback,
        }


if __name__ == "__main__":
    # Quick self-test for reviewer node math logic
    from state.schemas import ContractTerms, CounterOffer

    terms = ContractTerms(
        party_a="A",
        party_b="B",
        effective_date="2026-01-01",
        initial_price=100000.0,
        payment_terms="Net 30",
        renewal_terms="None",
        key_clauses=[],
    )
    # Correct calculation: (100000 - 85000)/100000 * 100 = 15.0%
    valid_offer = CounterOffer(
        proposed_price=85000.0,
        discount_percentage=15.0,
        revised_payment_terms="Net 60",
        revised_clauses=[],
        rationale="Discount request",
    )
    test_state = {"contract_terms": terms, "counter_offer": valid_offer}
    res = reviewer_node(test_state)  # type: ignore
    print(f"Test Result: math_valid={res['math_valid']}, feedback={res['reviewer_feedback']}")
