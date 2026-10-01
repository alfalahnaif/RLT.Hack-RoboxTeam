"""Typed inputs and outputs for historical supplier-pool analysis."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Literal


ScopeKind = Literal["okpd2_code", "okpd2_group", "okpd2_class"]


@dataclass(frozen=True)
class PoolScope:
    kind: ScopeKind
    value: str
    as_of: date | None = None
    recent_days: int = 365

    def __post_init__(self) -> None:
        if self.kind not in ("okpd2_code", "okpd2_group", "okpd2_class"):
            raise ValueError(f"Unsupported OKPD2 scope: {self.kind}")
        if not self.value or self.recent_days < 1:
            raise ValueError("Scope value and positive recent_days are required")


@dataclass(frozen=True)
class PoolThresholds:
    min_lots: int
    min_awards: int
    moderate_top1: float = .25
    high_top1: float = .50
    very_high_top1: float = .80
    moderate_hhi: float = .125
    high_hhi: float = .32
    very_high_hhi: float = .60

    def __post_init__(self) -> None:
        if self.min_lots < 1 or self.min_awards < 1:
            raise ValueError("Minimum support must be positive")
        if not (0 < self.moderate_top1 < self.high_top1 < self.very_high_top1 <= 1):
            raise ValueError("Top supplier thresholds must increase within (0, 1]")
        if not (0 < self.moderate_hhi < self.high_hhi < self.very_high_hhi <= 1):
            raise ValueError("HHI thresholds must increase within (0, 1]")


@dataclass(frozen=True)
class PoolSupport:
    lots: int
    procurements: int
    customers: int
    awards: int


@dataclass(frozen=True)
class PoolSuppliers:
    observed: int
    winning: int
    recent_winning: int
    em_observed: int
    em_winning: int
    ais_gz_winning: int


@dataclass(frozen=True)
class PoolConcentration:
    top1_share: float | None
    top3_share: float | None
    hhi: float | None
    label: str


@dataclass(frozen=True)
class PoolAlternatives:
    total_count: int
    winning_count: int
    observed_only_count: int
    suppliers: tuple[dict, ...]


@dataclass(frozen=True)
class PoolHealth:
    scope: PoolScope
    support: PoolSupport
    suppliers: PoolSuppliers
    concentration: PoolConcentration
    dominant_supplier: dict | None
    alternatives: PoolAlternatives
    reasons: tuple[str, ...]
    limitations: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)
