"""Data structures and the versioned configuration of the P1-002 baseline."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import date

BASELINE_VERSION = "1.0.0"


@dataclass(frozen=True)
class SearchConfig:
    # ---- query construction
    max_query_items: int = 8            # multi-item lots: keep the most informative distinct items (bounded work)
    max_or_lexemes: int = 6             # rarest lexemes OR-ed per query item for FTS retrieval
    max_df_ratio: float = 0.02          # lexemes in more than this share of snapshot documents are not used to retrieve
    min_tech_token_len: int = 5         # technical tokens (letters+digits) searched as exact substrings (trigram index)
    # ---- retrieval caps (per query item)
    text_items_limit: int = 300
    tech_items_limit: int = 100
    okpd2_exact_lots_limit: int = 300
    okpd2_broad_lots_limit: int = 200
    # ---- lot relevance (normalized weighted fusion of bounded branch similarities, each in [0, 1])
    w_lot_text: float = 0.6
    w_lot_okpd2: float = 0.3
    w_lot_subject: float = 0.1
    # ---- candidate generation
    historical_lot_limit: int = 300     # top relevant historical lots whose suppliers become candidates
    min_lot_relevance: float = 0.05
    # ---- supplier score (weights renormalized over applicable components)
    w_product_text: float = 0.25
    w_okpd2: float = 0.20
    w_historical_relevance: float = 0.20
    w_relevant_awards: float = 0.20
    w_em_participation: float = 0.05
    w_recency: float = 0.05
    w_same_customer: float = 0.05
    evidence_saturation: float = 3.0    # f(x) = 1 - exp(-x / s) for summed relevance-weighted evidence
    awards_saturation: float = 2.0
    participation_saturation: float = 3.0
    recency_half_life_days: int = 365   # 0.5 ** (age_days / half_life); 2024 evidence keeps weight
    top_k: int = 20
    # ---- P2-003 query-relative ranking options (all neutral by default -> P1-002 scores unchanged)
    w_evidence_quality: float = 0.0     # mean of the supplier's top-k relevant-lot relevances (zero-padded): quality, not volume
    quality_top_k: int = 3
    w_item_coverage: float = 0.0        # multi-item queries: mean over requested items of the supplier's best match for that item
    redundant_text_factor: float = 1.0  # product_text weight multiplier when every query item's text ~ the subject
    redundancy_jaccard: float = 0.8     # comparison-key token Jaccard at/above which item text counts as redundant with the subject
    # ---- P2-001 semantic candidate expansion (0 = disabled -> identical to P2-003 behaviour)
    semantic_top_k: int = 0             # nearest distinct historical texts per query item
    semantic_items_per_text: int = 5    # newest visible items mapped from each text (bounded: one text cannot flood the pool)
    semantic_weight: float = 0.8        # λ: per query item text match = max(lexical, λ * normalized semantic similarity)
    semantic_floor: float = 0.82        # cosine calibration from the feasibility study (not tuned on DEV): floor -> 0
    semantic_ceiling: float = 0.95      # ceiling -> 1
    semantic_ef_search: int = 200

    def with_(self, **kw) -> "SearchConfig":
        return replace(self, **kw)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class QueryItem:
    product_name: str            # normalized product text (normalize.py)
    okpd2: dict | None           # {"code", "class", "subclass", "group", "subgroup", "kind"} or None
    lexemes: list[str] = field(default_factory=list)       # russian-config lexemes
    tech_tokens: list[str] = field(default_factory=list)   # letter+digit tokens kept verbatim (a515-57-50r7, 4103dw)


@dataclass
class QueryLot:
    as_of: date
    subject: str | None
    items: list[QueryItem]
    customer_inn: str | None = None
    lot_id: str | None = None    # informational only (never used to look up its own suppliers)
    total_items: int = 0         # before the max_query_items cap
    subject_lexemes: list[str] = field(default_factory=list)  # weak supporting context only


# The configuration chosen by P1-002 on DEV (reports/p1_002_baseline.json) — frozen reference for P2-003.
P1_002_BASELINE = SearchConfig(evidence_saturation=10.0, awards_saturation=6.0, participation_saturation=6.0)

# P2-003 accepted challenger "C2 relevance-dominant" (reports/p2_003_ranking.json): weight moved from evidence volume to query relevance.
P2_003_RANKING = P1_002_BASELINE.with_(w_product_text=0.35, w_okpd2=0.30, w_historical_relevance=0.10, w_relevant_awards=0.10)

# P2-001 accepted configuration "S3 semantic top-100" (reports/p2_001_semantic.json): additive SEMANTIC retrieval branch,
# ranking weights unchanged from P2-003. Degrades to P2-003 behaviour with a warning when the model/index is unavailable.
P2_001_SEMANTIC = P2_003_RANKING.with_(semantic_top_k=100)

# Configuration used by `recommend lot` (the CLI).
DEFAULT_CONFIG = P2_001_SEMANTIC
