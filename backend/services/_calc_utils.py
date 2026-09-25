"""
Shared calculation utilities for all services.

Single place to control output precision across all calculation endpoints.
To change decimal places globally, update OUTPUT_DECIMAL_PLACES here.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from pydantic import BaseModel, model_validator

OUTPUT_DECIMAL_PLACES: int = 6
_QUANT = Decimal("0." + "0" * OUTPUT_DECIMAL_PLACES)  # Decimal("0.000001")


def round_result(value: Optional[float]) -> Optional[float]:
    """Apply precision to OUTPUT_DECIMAL_PLACES decimal places. Returns None if value is None."""
    if value is None:
        return None
    return round(value, OUTPUT_DECIMAL_PLACES)


def round_decimal(value: Optional[Decimal]) -> Optional[Decimal]:
    """Round a Decimal to OUTPUT_DECIMAL_PLACES. Returns None if value is None."""
    if value is None:
        return None
    return value.quantize(_QUANT, rounding=ROUND_HALF_UP)


class DashboardBase(BaseModel):
    """Base Pydantic model for all dashboard response models.

    Automatically rounds all Decimal and List[Optional[Decimal]] fields to
    OUTPUT_DECIMAL_PLACES on construction, ensuring consistent precision across
    all dashboard API outputs. To change global precision, update OUTPUT_DECIMAL_PLACES.
    """

    @model_validator(mode="after")
    def _round_decimal_fields(self) -> "DashboardBase":
        for field_name in self.model_fields:
            value = getattr(self, field_name)
            if isinstance(value, Decimal):
                object.__setattr__(self, field_name, round_decimal(value))
            elif isinstance(value, list) and any(isinstance(v, Decimal) for v in value):
                object.__setattr__(
                    self,
                    field_name,
                    [round_decimal(v) if isinstance(v, Decimal) else v for v in value],
                )
        return self
