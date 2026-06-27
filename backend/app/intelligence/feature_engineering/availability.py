"""Availability features: how easily a candidate can actually be hired."""

from __future__ import annotations

from app.intelligence.domain import Candidate

# Notice-period thresholds (days). The JD prefers <=30 day notice and is
# willing to buy out up to 30 more; longer notices raise the bar.
_NOTICE_IDEAL_MAX = 30
_NOTICE_ACCEPTABLE_MAX = 60
_NOTICE_HARD_CAP = 120


def _notice_score(notice_days: int | None) -> float:
    """Map notice period in days to a [0, 1] availability score."""
    if notice_days is None:
        return 0.5
    if notice_days <= _NOTICE_IDEAL_MAX:
        return 1.0
    if notice_days <= _NOTICE_ACCEPTABLE_MAX:
        return 0.7
    if notice_days <= _NOTICE_HARD_CAP:
        return 0.4
    return 0.1


def availability_score(candidate: Candidate) -> float:
    """Composite [0, 1] availability score.

    Components:
        * Notice period (60%)
        * Open-to-work flag (25%)
        * Verified contact (email or phone) (15%)

    Args:
        candidate: The candidate.

    Returns:
        Availability score in [0, 1].
    """
    s = candidate.signals

    notice = _notice_score(s.notice_period_days)

    if s.open_to_work_flag is True:
        otw = 1.0
    elif s.open_to_work_flag is False:
        otw = 0.2
    else:
        otw = 0.5

    contact = 0.5
    if s.verified_email or s.verified_phone:
        contact = 1.0
    elif s.verified_email is False and s.verified_phone is False:
        contact = 0.2

    return round(0.6 * notice + 0.25 * otw + 0.15 * contact, 4)
