"""Genuinely cross-feature API response contracts."""

from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard API error response."""

    detail: str = Field(..., description="Error message", json_schema_extra={"example": "Stream not found"})


class RateLimitErrorResponse(BaseModel):
    """SlowAPI rate-limit response body."""

    error: str = Field(..., description="Rate limit error", json_schema_extra={"example": "Rate limit exceeded"})


class ValidationIssue(BaseModel):
    loc: list[str | int]
    msg: str
    type: str
    input: Any | None = None
    ctx: dict[str, Any] | None = None


class ValidationErrorResponse(BaseModel):
    detail: list[ValidationIssue]


ErrorOrValidationResponse = ErrorResponse | ValidationErrorResponse


class MessageResponse(BaseModel):
    message: str
