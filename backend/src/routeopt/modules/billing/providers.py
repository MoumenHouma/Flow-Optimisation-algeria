"""Payment providers (F19).

Algerian SaaS payment is mostly offline: the manager pays by CCP transfer,
BaridiMob or cash and the invoice is confirmed manually. A Stripe path is stubbed
behind the same interface for card-capable Enterprise clients; it is only wired
when ``settings.stripe_secret_key`` is configured.
"""

from typing import Protocol

from routeopt.core.exceptions import ValidationError


class PaymentProvider(Protocol):
    name: str

    def confirm(self, amount_da: float, reference: str | None) -> str:
        """Confirm a payment, returning a settlement reference. Raises on failure."""
        ...


class ManualProvider:
    """Offline payment (CCP / BaridiMob / cash): trust the manager-supplied receipt."""

    name = "manual"

    def confirm(self, amount_da: float, reference: str | None) -> str:
        # Nothing to charge — the money moved outside the system. Keep the receipt.
        return reference or "manual"


class StripeProvider:
    """Card payment via Stripe — stubbed until a live key is configured."""

    name = "stripe"

    def confirm(self, amount_da: float, reference: str | None) -> str:
        raise ValidationError(
            "Stripe payments are not enabled on this deployment; "
            "record the payment via CCP/BaridiMob/cash instead."
        )
