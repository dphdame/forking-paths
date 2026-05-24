"""forking-paths: provenance audit for AI-assisted empirical research."""

from forking_paths.classify import DecisionCensus, classify_turns
from forking_paths.compare import (
    ComparisonReport,
    Deviation,
    compare_session_to_prereg,
)
from forking_paths.fingerprint import (
    SpecFingerprint,
    fingerprint_command,
    detect_family,
)
from forking_paths.flag import AbandonmentFlag, flag_context_sensitive_abandonment
from forking_paths.ledger_audit import (
    LedgerEntry,
    OVB_MENU,
    SessionAudit,
    SpecMenu,
    audit_session_path,
    audit_session_turns,
    parse_ledger,
    parse_specs_candidate,
)
from forking_paths.parser import Turn, parse_session
from forking_paths.prereg import Prereg, parse_prereg
from forking_paths.report import build_report

__version__ = "0.4.0"

__all__ = [
    "Turn",
    "parse_session",
    "classify_turns",
    "DecisionCensus",
    "flag_context_sensitive_abandonment",
    "AbandonmentFlag",
    "build_report",
    "Prereg",
    "parse_prereg",
    "ComparisonReport",
    "Deviation",
    "compare_session_to_prereg",
    "SpecFingerprint",
    "fingerprint_command",
    "detect_family",
    "SpecMenu",
    "OVB_MENU",
    "SessionAudit",
    "LedgerEntry",
    "audit_session_turns",
    "audit_session_path",
    "parse_ledger",
    "parse_specs_candidate",
]
