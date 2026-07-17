from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class SubscriptionSchema(BaseModel):
    """
    Base schema for subscription and billing API models.
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
        use_enum_values=False,
    )


class BillingInterval(StrEnum):
    MONTH = "month"
    YEAR = "year"


class SubscriptionStatus(StrEnum):
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    UNPAID = "unpaid"


class PlanTier(StrEnum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"


class CheckoutMode(StrEnum):
    SUBSCRIPTION = "subscription"


class CancellationTiming(StrEnum):
    PERIOD_END = "period_end"
    IMMEDIATE = "immediate"


class PlanFeature(SubscriptionSchema):
    """
    One user-facing subscription-plan feature.
    """

    key: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1_000)
    included: bool = True
    limit: int | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=100)


class SubscriptionPlan(SubscriptionSchema):
    """
    Public subscription plan.

    Provider-specific product and price identifiers are intentionally omitted.
    The public plan ID is resolved to trusted provider configuration inside the
    Billing Service.
    """

    id: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9][a-z0-9_-]*$",
    )
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2_000)
    tier: PlanTier
    billing_interval: BillingInterval
    currency: str = Field(
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$",
    )
    unit_amount: int = Field(
        ge=0,
        description="Price in the smallest currency unit, such as cents.",
    )
    trial_days: int = Field(default=0, ge=0, le=365)
    features: list[PlanFeature] = Field(default_factory=list)
    is_active: bool = True
    is_recommended: bool = False


class PlanListResponse(SubscriptionSchema):
    """
    Public list of purchasable subscription plans.
    """

    items: list[SubscriptionPlan]
    default_currency: str = Field(
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$",
    )


class CheckoutSessionRequest(SubscriptionSchema):
    """
    Request to create a hosted subscription checkout session.

    The client supplies a public plan identifier, never a trusted monetary
    amount or payment-provider price identifier.
    """

    plan_id: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9][a-z0-9_-]*$",
    )
    success_url: HttpUrl
    cancel_url: HttpUrl
    promotion_code: str | None = Field(default=None, max_length=100)
    allow_promotion_codes: bool = True
    client_reference: str | None = Field(default=None, max_length=200)


class CheckoutSessionResponse(SubscriptionSchema):
    """
    Hosted checkout-session information.
    """

    session_id: str = Field(min_length=1, max_length=500)
    checkout_url: HttpUrl
    expires_at: datetime
    mode: CheckoutMode = CheckoutMode.SUBSCRIPTION


class CustomerPortalResponse(SubscriptionSchema):
    """
    Hosted customer billing-portal session.
    """

    portal_url: HttpUrl
    expires_at: datetime | None = None


class SubscriptionUsage(SubscriptionSchema):
    """
    Current-period product usage and quota information.
    """

    analysis_count: int = Field(default=0, ge=0)
    analysis_limit: int | None = Field(default=None, ge=0)
    storage_bytes: int = Field(default=0, ge=0)
    storage_limit_bytes: int | None = Field(default=None, ge=0)
    video_minutes: float = Field(default=0, ge=0)
    video_minutes_limit: float | None = Field(default=None, ge=0)
    period_started_at: datetime | None = None
    period_ends_at: datetime | None = None


class SubscriptionResponse(SubscriptionSchema):
    """
    Public representation of the user's subscription.

    Payment method details, complete provider customer identifiers, invoices,
    and provider secrets must not be returned through this model.
    """

    id: UUID
    user_id: UUID
    plan: SubscriptionPlan
    status: SubscriptionStatus
    billing_interval: BillingInterval
    currency: str = Field(
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$",
    )
    unit_amount: int = Field(ge=0)
    quantity: int = Field(default=1, ge=1, le=100)
    usage: SubscriptionUsage | None = None
    cancel_at_period_end: bool = False
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    trial_start: datetime | None = None
    trial_end: datetime | None = None
    cancelled_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateSubscriptionRequest(SubscriptionSchema):
    """
    Request to change an existing subscription.

    At least one field must be provided. The Billing Service determines
    proration, entitlement timing, and provider synchronization.
    """

    plan_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9][a-z0-9_-]*$",
    )
    quantity: int | None = Field(default=None, ge=1, le=100)
    promotion_code: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def require_update(self) -> UpdateSubscriptionRequest:
        if (
            self.plan_id is None
            and self.quantity is None
            and self.promotion_code is None
        ):
            raise ValueError(
                "At least one subscription update field must be provided."
            )

        return self


class CancelSubscriptionRequest(SubscriptionSchema):
    """
    Request to cancel a subscription.
    """

    timing: CancellationTiming = CancellationTiming.PERIOD_END
    reason: str | None = Field(default=None, max_length=1_000)
    feedback_code: str | None = Field(default=None, max_length=100)
