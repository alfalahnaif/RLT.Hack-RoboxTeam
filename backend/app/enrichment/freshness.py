"""P5-001A centralized freshness / cache policy for Supplier 360 enrichment (one place, versioned with the code).

Principle carried over from P4-005C: *retrieved today* is not *fresh information*. Freshness of a contact describes the
source page (content currency), not the retrieval time:
  - page OUTDATED (latest copyright/news year older than CURRENT_YEAR_WINDOW)      -> STALE, even if checked today
  - page UNDATED (no dating signal)                                                 -> UNKNOWN
  - page CURRENT and checked within CONTACT_FRESH_DAYS                              -> FRESH, else STALE
Registry identity is FRESH while checked within IDENTITY_FRESH_DAYS. No legal claim is made from freshness.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

FRESH, STALE, UNKNOWN = "FRESH", "STALE", "UNKNOWN"
CURRENT, UNDATED, OUTDATED = "CURRENT", "UNDATED", "OUTDATED"


@dataclass(frozen=True)
class FreshnessPolicy:
    version: str = "p5-001a-v1"
    contact_fresh_days: int = 180          # same window as P4-005C (contacts.FRESH_DAYS)
    identity_fresh_days: int = 90          # registry identity re-check window
    current_year_window: int = 1           # a page dated this year or last year counts as CURRENT
    profile_ttl_days: int = 30             # cached COMPLETE / PARTIAL profiles are reused within this window
    failed_retry_after_hours: int = 24     # a retryable FAILED profile may be re-attempted after this delay
    in_progress_timeout_minutes: int = 15  # an IN_PROGRESS row older than this is treated as abandoned (retryable)


POLICY = FreshnessPolicy()


def content_currency(latest_year: int | None, today: date, policy: FreshnessPolicy = POLICY) -> str:
    if latest_year is None:
        return UNDATED
    return CURRENT if latest_year >= today.year - policy.current_year_window else OUTDATED


def contact_freshness(checked_at: datetime | None, currency: str | None, today: date, policy: FreshnessPolicy = POLICY) -> str:
    if checked_at is None:
        return UNKNOWN
    if currency == OUTDATED:
        return STALE
    if currency in (None, UNDATED):
        return UNKNOWN
    return FRESH if (today - checked_at.date()).days <= policy.contact_fresh_days else STALE


def identity_freshness(checked_at: datetime | None, today: date, policy: FreshnessPolicy = POLICY) -> str:
    if checked_at is None:
        return UNKNOWN
    return FRESH if (today - checked_at.date()).days <= policy.identity_fresh_days else STALE


def cache_reusable(status: str, retryable: bool, last_enriched_at: datetime | None, updated_at: datetime | None,
                   now: datetime, policy: FreshnessPolicy = POLICY) -> bool:
    """True when a stored profile must be returned instead of re-querying sources (no explicit refresh)."""
    if status in ("COMPLETE", "PARTIAL"):
        return last_enriched_at is not None and now - last_enriched_at <= timedelta(days=policy.profile_ttl_days)
    if status == "FAILED":
        return not retryable or (updated_at is not None and now - updated_at < timedelta(hours=policy.failed_retry_after_hours))
    if status == "IN_PROGRESS":
        return updated_at is not None and now - updated_at < timedelta(minutes=policy.in_progress_timeout_minutes)
    return False
