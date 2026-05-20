"""forking-paths: provenance audit for AI-assisted empirical research."""

from forking_paths.classify import DecisionCensus, classify_turns
from forking_paths.compare import (
    ComparisonReport,
    Deviation,
    compare_session_to_prereg,
)
from forking_paths.flag import AbandonmentFlag, flag_context_sensitive_abandonment
from forking_paths.parser import Turn, parse_session
from forking_paths.prereg import Prereg, parse_prereg
from forking_paths.report import build_report

__version__ = "0.2.0"

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
]
