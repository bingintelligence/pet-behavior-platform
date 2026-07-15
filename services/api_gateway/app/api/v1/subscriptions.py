from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.core.dependencies import (
    get_billing_client,
    get_current_user,
)
from app.schemas.subscription import (
    CancelSubscriptionRequest,
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    CustomerPortalResponse,
    PlanListResponse,
    SubscriptionResponse,
    UpdateSubscriptionRequest,
)
from app.services.billing_client import BillingClient
from shared.schemas.auth import AuthenticatedUser

router = APIRouter(
    prefix="/subscriptions",
    tags=["Subscriptions"],
)

BillingClientDependency = Annotated[
    BillingClient,
    Depends(get_billing_client),
]

CurrentUserDependency = Annotated[
    AuthenticatedUser,
    Depends(get_current_user),
]


@router.get(
    "/plans",
    response_model=PlanListResponse,
    status_code=status.HTTP_200_OK,
    summary="List subscription plans",
)
async def list_subscription_plans(
    request: Request,
    billing_client: BillingClientDependency,
) -> PlanListResponse:
    """
    Return public subscription plans and pricing information.

    The Billing Service should return only active, customer-facing plans.
    Internal payment-provider price identifiers should not be exposed unless
    they are intentionally used as public plan identifiers.
    """
    return await billing_client.list_plans(
        request_id=_get_request_id(request),
    )


@router.get(
    "/me",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the current subscription",
)
async def get_current_subscription(
    request: Request,
    billing_client: BillingClientDependency,
    current_user: CurrentUserDependency,
) -> SubscriptionResponse:
    """
    Return the authenticated user's current subscription and usage limits.
    """
    return await billing_client.get_subscription(
        user_id=current_user.user_id,
        request_id=_get_request_id(request),
    )


@router.post(
    "/checkout-session",
    response_model=CheckoutSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a checkout session",
)
async def create_checkout_session(
    payload: CheckoutSessionRequest,
    request: Request,
    billing_client: BillingClientDependency,
    current_user: CurrentUserDependency,
) -> CheckoutSessionResponse:
    """
    Create a hosted checkout session for a subscription purchase.

    The Billing Service must select price identifiers from trusted server-side
    configuration. It must not trust an arbitrary price or amount supplied by
    the client.
    """
    return await billing_client.create_checkout_session(
        user_id=current_user.user_id,
        payload=payload,
        request_id=_get_request_id(request),
        idempotency_key=request.headers.get("idempotency-key"),
    )


@router.post(
    "/customer-portal",
    response_model=CustomerPortalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a billing portal session",
)
async def create_customer_portal_session(
    request: Request,
    billing_client: BillingClientDependency,
    current_user: CurrentUserDependency,
) -> CustomerPortalResponse:
    """
    Create a short-lived customer billing portal session.

    The portal can be used to update payment methods, view invoices, or manage
    the subscription through the configured payment provider.
    """
    return await billing_client.create_customer_portal_session(
        user_id=current_user.user_id,
        request_id=_get_request_id(request),
    )


@router.patch(
    "/{subscription_id}",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a subscription",
)
async def update_subscription(
    subscription_id: UUID,
    payload: UpdateSubscriptionRequest,
    request: Request,
    billing_client: BillingClientDependency,
    current_user: CurrentUserDependency,
) -> SubscriptionResponse:
    """
    Change the current subscription plan or billing configuration.

    The Billing Service is responsible for ownership validation, proration,
    provider communication, and synchronization of local subscription state.
    """
    return await billing_client.update_subscription(
        user_id=current_user.user_id,
        subscription_id=subscription_id,
        payload=payload,
        request_id=_get_request_id(request),
        idempotency_key=request.headers.get("idempotency-key"),
    )


@router.post(
    "/{subscription_id}/cancel",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel a subscription",
)
async def cancel_subscription(
    subscription_id: UUID,
    payload: CancelSubscriptionRequest,
    request: Request,
    billing_client: BillingClientDependency,
    current_user: CurrentUserDependency,
) -> SubscriptionResponse:
    """
    Cancel a subscription immediately or at the end of the billing period.
    """
    return await billing_client.cancel_subscription(
        user_id=current_user.user_id,
        subscription_id=subscription_id,
        payload=payload,
        request_id=_get_request_id(request),
        idempotency_key=request.headers.get("idempotency-key"),
    )


@router.post(
    "/{subscription_id}/resume",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Resume a subscription",
)
async def resume_subscription(
    subscription_id: UUID,
    request: Request,
    billing_client: BillingClientDependency,
    current_user: CurrentUserDependency,
) -> SubscriptionResponse:
    """
    Remove a pending end-of-period cancellation when the provider allows it.
    """
    return await billing_client.resume_subscription(
        user_id=current_user.user_id,
        subscription_id=subscription_id,
        request_id=_get_request_id(request),
        idempotency_key=request.headers.get("idempotency-key"),
    )


def _get_request_id(request: Request) -> str | None:
    """
    Return the request ID generated by request-ID middleware.
    """
    return getattr(request.state, "request_id", None)
