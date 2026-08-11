import logging
from typing import Dict, Any, Optional

try:
    import resend
except ImportError:
    resend = None

from config.settings import settings
from state.schemas import CounterOffer, ContractTerms

logger = logging.getLogger(__name__)


def dispatch_counter_offer_email(
    contract_terms: Optional[ContractTerms],
    counter_offer: Optional[CounterOffer],
    recipient_email: Optional[str] = None,
) -> Dict[str, Any]:
    """Side Effect Execution: Dispatches the finalized counter offer email via Resend API."""
    target_email = recipient_email or settings.recipient_email
    sender_email = settings.sender_email
    api_key = settings.resend_api_key

    party_a = contract_terms.party_a if contract_terms else "Vendor"
    party_b = contract_terms.party_b if contract_terms else "Client"
    initial_price = contract_terms.initial_price if contract_terms else 0.0

    proposed_price = counter_offer.proposed_price if counter_offer else 0.0
    discount_pct = counter_offer.discount_percentage if counter_offer else 0.0
    revised_terms = counter_offer.revised_payment_terms if counter_offer else "Net 60"
    rationale = counter_offer.rationale if counter_offer else "Negotiated corporate terms"

    subject = f"Official Counter-Offer Proposal: Contract Negotiation ({party_b} & {party_a})"

    html_content = f"""
    <h2>Contract Counter-Offer Proposal</h2>
    <p>Dear {party_a} Legal & Procurement Team,</p>
    
    <p>On behalf of <strong>{party_b}</strong>, we have reviewed the initial contract proposal and submit the following counter-offer terms:</p>
    
    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; font-family: sans-serif;">
        <tr style="background-color: #f2f2f2;">
            <th>Term Description</th>
            <th>Original Offer</th>
            <th>Proposed Counter-Offer</th>
        </tr>
        <tr>
            <td><strong>Contract Price</strong></td>
            <td>${initial_price:,.2f}</td>
            <td><strong>${proposed_price:,.2f}</strong> ({discount_pct:.1f}% discount)</td>
        </tr>
        <tr>
            <td><strong>Payment Terms</strong></td>
            <td>{contract_terms.payment_terms if contract_terms else 'N/A'}</td>
            <td><strong>{revised_terms}</strong></td>
        </tr>
    </table>
    
    <h3>Business Rationale</h3>
    <p>{rationale}</p>
    
    <h3>Revised Clauses</h3>
    <ul>
        {''.join(f'<li>{clause}</li>' for clause in (counter_offer.revised_clauses if counter_offer else []))}
    </ul>
    
    <p>We look forward to finalizing this agreement.</p>
    <p>Best regards,<br><em>Contract Negotiator Swarm System</em></p>
    """

    if not api_key or not resend:
        logger.warning(
            "RESEND_API_KEY not configured or resend library missing. Simulating email dispatch for testing."
        )
        return {
            "status": "simulated_success",
            "message": f"Simulated email sent to {target_email}",
            "subject": subject,
            "recipient": target_email,
        }

    try:
        resend.api_key = api_key
        params: resend.Emails.SendParams = {
            "from": sender_email,
            "to": [target_email],
            "subject": subject,
            "html": html_content,
        }

        email_response = resend.Emails.send(params)
        logger.info(f"Resend email dispatched successfully: {email_response}")
        return {
            "status": "success",
            "email_id": email_response.get("id", "unknown"),
            "recipient": target_email,
        }
    except Exception as e:
        logger.error(f"Failed to dispatch email via Resend: {e}")
        return {
            "status": "error",
            "message": f"Resend email failed: {str(e)}",
            "recipient": target_email,
        }
