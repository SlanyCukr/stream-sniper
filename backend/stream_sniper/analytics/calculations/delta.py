"""Single owner for "percent change vs a prior/baseline value" and its zero-baseline policy.

Three call sites derive velocity from a *current* value and a *prior*/baseline value
(the Discord digest's velocity labels, the API's scene-trend classification, and the
stream report card's baseline deltas). They agree on the underlying math but render it
differently, so the *decisions* live here and callers own only their presentation:

* ``prior == 0`` and ``current == 0`` -> :attr:`DeltaTrend.NO_CHANGE`
  (an all-zero window has not moved -- not "new").
* ``prior == 0`` and ``current > 0``  -> :attr:`DeltaTrend.NEW`
  (no baseline exists, so a percent would be meaningless/unbounded).
* ``current == prior`` (non-zero)     -> :attr:`DeltaTrend.NO_CHANGE`
  (exactly 0% -- never rendered as a signed "0").
* otherwise                           -> :attr:`DeltaTrend.RISING` / :attr:`DeltaTrend.FALLING`.

:func:`percent_change` returns the signed percent, or ``None`` when there is no baseline
(``prior == 0``) -- matching the "``delta_pct`` is null when prior is 0" wire contract.
"""

from enum import Enum


class DeltaTrend(Enum):
    """How a current value moved against its prior/baseline value."""

    NO_CHANGE = "no_change"
    NEW = "new"
    RISING = "rising"
    FALLING = "falling"


def classify_delta(current: float, prior: float) -> DeltaTrend:
    """Bucket ``current`` against its ``prior``/baseline (see the module docstring).

    ``current == prior`` is checked first, so an all-zero ``(0, 0)`` reads as
    NO_CHANGE rather than NEW; a zero baseline only means NEW when ``current`` grew.
    """
    if current == prior:
        return DeltaTrend.NO_CHANGE
    if prior == 0:
        return DeltaTrend.NEW
    return DeltaTrend.RISING if current > prior else DeltaTrend.FALLING


def percent_change(current: float, prior: float, *, digits: int | None = 1) -> float | None:
    """Signed percent change of ``current`` vs ``prior``, or ``None`` when ``prior`` is 0.

    ``digits`` is forwarded to :func:`round`: an int rounds to that many decimals
    (returning a ``float``); ``None`` rounds to the nearest whole number (returning
    an ``int``). ``prior == 0`` yields ``None`` because there is no baseline to divide by.
    """
    if prior == 0:
        return None
    return round(100 * (current - prior) / prior, digits)
