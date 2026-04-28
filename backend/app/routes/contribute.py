"""Contribution routes for voluntary tip jar functionality using Stripe.

Aggregation Strategy:
- Each contribution updates daily and all-time aggregate documents
- contribution_stats() reads 30 daily docs instead of scanning 10k contributions
- Daily docs: contributions_aggregates/daily/{YYYY-MM-DD}
- All-time totals: contributions_aggregates/totals/all_time
"""

import asyncio
import hmac
import logging
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import settings
from app.rate_limiter import limiter
from app.services.analytics import EventType, track_event
from app.store import session_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/contribute", tags=["contribute"])

# Firestore collections for contributions
_CONTRIBUTIONS_COLLECTION = "contributions"
_CONTRIBUTIONS_AGGREGATES_COLLECTION = "contributions_aggregates"

# Stripe client (lazily initialized)
_stripe_client = None


def _get_stripe():
    """Get or create Stripe client."""
    global _stripe_client
    if _stripe_client is None:
        if not settings.ENABLE_CONTRIBUTIONS:
            return None
        if not settings.STRIPE_SECRET_KEY:
            logger.warning("STRIPE_SECRET_KEY not set, contributions disabled")
            return None
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        _stripe_client = stripe
    return _stripe_client


def _get_firestore():
    """Get the shared Firestore client for contribution records."""
    if not settings.USE_FIRESTORE:
        return None
    from app.store.firestore_client import get_client
    return get_client()


class CheckoutRequest(BaseModel):
    """Request to create a contribution checkout session."""
    amount_cents: int = Field(..., ge=100, le=50000, description="Amount in cents (100-50000)")
    session_id: UUID = Field(..., description="Narrative session ID")
    email: Optional[str] = Field(None, description="Optional email for receipt")


class CheckoutResponse(BaseModel):
    """Response with Stripe checkout URL."""
    checkout_url: str


class ContributionStats(BaseModel):
    """Aggregate contribution statistics."""
    period: str
    total_contributions: int
    total_amount_cents: int
    average_amount_cents: float
    contribution_count_by_amount: dict[int, int]


@router.post("/checkout", response_model=CheckoutResponse)
@limiter.limit("5/minute")
async def create_checkout(request: Request, body: CheckoutRequest):
    """
    Create a Stripe Checkout session for a contribution.

    Rate limited to 5 requests per minute per IP.
    Returns checkout URL for redirect.
    """
    if not settings.ENABLE_CONTRIBUTIONS:
        raise HTTPException(status_code=503, detail="Contributions are not enabled")

    stripe = _get_stripe()
    if not stripe:
        raise HTTPException(status_code=503, detail="Payment processing unavailable")

    # Verify session exists
    session = session_store.get(str(body.session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Narrative session not found")

    # Get region for analytics
    region = session.user_input.region_of_origin if session.user_input else None

    # Track checkout started event
    await track_event(
        EventType.TIP_CHECKOUT_STARTED,
        str(body.session_id),
        region=region,
        metadata={"amount_cents": body.amount_cents}
    )

    try:
        # Create Stripe Checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "Support the Griot",
                        "description": "A voluntary contribution to support Sankofa's mission of preserving ancestral narratives.",
                    },
                    "unit_amount": body.amount_cents,
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{settings.FRONTEND_URL}/narrative/{body.session_id}?contributed=true",
            cancel_url=f"{settings.FRONTEND_URL}/narrative/{body.session_id}",
            customer_email=body.email,
            metadata={
                "session_id": str(body.session_id),
                "region_of_origin": region or "",
            },
        )

        logger.info(
            "Checkout session created: %s for narrative %s, amount: %d cents",
            checkout_session.id, body.session_id, body.amount_cents
        )

        return CheckoutResponse(checkout_url=checkout_session.url)

    except Exception as e:
        logger.error("Failed to create Stripe checkout session: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events.

    Validates webhook signature and records completed contributions.
    """
    if not settings.ENABLE_CONTRIBUTIONS:
        raise HTTPException(status_code=503, detail="Contributions are not enabled")

    stripe = _get_stripe()
    if not stripe:
        raise HTTPException(status_code=503, detail="Payment processing unavailable")

    # Get raw body for signature verification
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        logger.warning("Webhook received without signature")
        raise HTTPException(status_code=400, detail="Missing signature")

    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=500, detail="Webhook not configured")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        logger.warning("Invalid webhook payload")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        logger.warning("Invalid webhook signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle checkout.session.completed
    if event["type"] == "checkout.session.completed":
        checkout_session = event["data"]["object"]

        session_id = checkout_session.get("metadata", {}).get("session_id", "")
        region = checkout_session.get("metadata", {}).get("region_of_origin", "")
        amount_cents = checkout_session.get("amount_total", 0)
        email = checkout_session.get("customer_email")
        stripe_session_id = checkout_session.get("id", "")

        logger.info(
            "Contribution completed: %s, session: %s, amount: %d cents",
            stripe_session_id, session_id, amount_cents
        )

        # Record contribution in Firestore
        await _record_contribution(
            session_id=session_id,
            amount_cents=amount_cents,
            stripe_session_id=stripe_session_id,
            email=email,
            region_of_origin=region,
        )

        # Track completion event
        if session_id:
            await track_event(
                EventType.TIP_COMPLETED,
                session_id,
                region=region,
                metadata={"amount_cents": amount_cents}
            )

    return {"received": True}


async def _record_contribution(
    session_id: str,
    amount_cents: int,
    stripe_session_id: str,
    email: Optional[str],
    region_of_origin: Optional[str],
) -> None:
    """Record a completed contribution in Firestore.

    Also updates daily and all-time aggregate documents for efficient stats queries.
    """
    client = _get_firestore()
    if not client:
        logger.info("Firestore disabled, skipping contribution record")
        return

    doc = {
        "session_id": session_id,
        "amount_cents": amount_cents,
        "currency": "usd",
        "stripe_session_id": stripe_session_id,
        "email": email,
        "region_of_origin": region_of_origin,
        "created_at": time.time(),
        "status": "completed",
    }

    try:
        # Write contribution and update aggregates in parallel
        await asyncio.gather(
            asyncio.to_thread(lambda: client.collection(_CONTRIBUTIONS_COLLECTION).add(doc)),
            _update_contribution_aggregates(client, amount_cents),
        )
        logger.debug("Contribution recorded: %s", stripe_session_id)
    except Exception as e:
        logger.error("Failed to record contribution: %s", e, exc_info=True)


async def _update_contribution_aggregates(client, amount_cents: int) -> None:
    """Update daily and all-time contribution aggregate documents.

    Daily doc structure: contributions_aggregates/daily/{YYYY-MM-DD}
    {
        "date": "2024-01-15",
        "total_contributions": 5,
        "total_amount_cents": 2500,
        "count_by_amount": {"500": 2, "1000": 3}
    }

    All-time doc structure: contributions_aggregates/totals/all_time
    {
        "total_contributions": 100,
        "total_amount_cents": 50000
    }
    """
    try:
        from google.cloud import firestore as fs

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Update daily aggregate
        daily_ref = client.collection(_CONTRIBUTIONS_AGGREGATES_COLLECTION).document(f"daily/{today}")
        daily_updates = {
            "date": today,
            "total_contributions": fs.Increment(1),
            "total_amount_cents": fs.Increment(amount_cents),
            f"count_by_amount.{amount_cents}": fs.Increment(1),
        }

        # Update all-time totals
        totals_ref = client.collection(_CONTRIBUTIONS_AGGREGATES_COLLECTION).document("totals/all_time")
        totals_updates = {
            "total_contributions": fs.Increment(1),
            "total_amount_cents": fs.Increment(amount_cents),
        }

        # Execute both updates
        await asyncio.gather(
            asyncio.to_thread(lambda: daily_ref.set(daily_updates, merge=True)),
            asyncio.to_thread(lambda: totals_ref.set(totals_updates, merge=True)),
        )

    except Exception as e:
        # Don't let aggregate errors affect the main contribution record
        logger.warning("[contributions] Aggregate update failed: %s", e)


@router.get("/stats")
@limiter.limit("10/minute")
async def contribution_stats(request: Request, authorization: str = Header(None)):
    """
    Get aggregate contribution statistics (key-protected via Authorization header).

    Reads from pre-computed daily aggregate documents instead of scanning
    all contributions. This reduces Firestore reads from ~10,000 to 30.

    Headers:
        Authorization: Bearer <ANALYTICS_KEY>
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required (Bearer <key>)")

    key = authorization.split(" ", 1)[1]
    if not hmac.compare_digest(key, settings.ANALYTICS_KEY):
        raise HTTPException(status_code=401, detail="Invalid access key")

    if not settings.USE_FIRESTORE:
        return {"error": "Statistics not available (Firestore disabled)"}

    client = _get_firestore()
    if not client:
        return {"error": "Firestore client not available"}

    try:
        # Generate date strings for the last 30 days
        today = datetime.now(timezone.utc)
        date_strings = [
            (today - __import__("datetime").timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(30)
        ]

        # Read all 30 daily aggregate docs
        def fetch_daily_docs():
            docs = []
            for date_str in date_strings:
                doc_ref = client.collection(_CONTRIBUTIONS_AGGREGATES_COLLECTION).document(f"daily/{date_str}")
                doc = doc_ref.get()
                if doc.exists:
                    docs.append(doc.to_dict())
            return docs

        daily_docs = await asyncio.to_thread(fetch_daily_docs)

        # Aggregate across days
        total_contributions = 0
        total_amount = 0
        count_by_amount: dict[int, int] = {}

        for doc_data in daily_docs:
            total_contributions += doc_data.get("total_contributions", 0)
            total_amount += doc_data.get("total_amount_cents", 0)

            # Merge count_by_amount
            for amount_str, count in doc_data.get("count_by_amount", {}).items():
                amount = int(amount_str)
                count_by_amount[amount] = count_by_amount.get(amount, 0) + count

        avg_amount = total_amount / total_contributions if total_contributions > 0 else 0

        return {
            "period": "last_30_days",
            "total_contributions": total_contributions,
            "total_amount_cents": total_amount,
            "average_amount_cents": round(avg_amount, 2),
            "contribution_count_by_amount": dict(sorted(count_by_amount.items())),
        }

    except Exception as e:
        logger.error("Failed to fetch contribution stats: %s", e, exc_info=True)
        return {"error": "Failed to fetch statistics"}
