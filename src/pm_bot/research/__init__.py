"""Replay and backtest entry points."""

from pm_bot.research.autoresearch import (
    AutoresearchReport,
    format_autoresearch_report,
    generate_autoresearch_report,
    write_autoresearch_report,
)
from pm_bot.research.backtest import run_backtest
from pm_bot.research.engine import (
    ResearchRunResult,
    format_research_summary,
    load_market_snapshots,
    run_replay_snapshots,
)
from pm_bot.research.experiments import (
    FixedWindowExperimentReport,
    format_fixed_window_report,
    run_fixed_window_experiments,
    write_fixed_window_report,
)
from pm_bot.research.paper_integrity import (
    PaperIntegrityReport,
    format_paper_integrity_report,
    generate_paper_integrity_report,
    write_paper_integrity_report,
)
from pm_bot.research.phase1_runner import (
    Phase1ReplayResult,
    default_phase1_config_dir,
    format_phase1_replay_result,
    run_phase1_replay,
)
from pm_bot.research.replay_determinism import (
    ReplayDeterminismReport,
    format_replay_determinism_report,
    generate_replay_determinism_report,
    write_replay_determinism_report,
)
from pm_bot.research.replay import run_replay
from pm_bot.research.window_mining import (
    WindowMiningReport,
    format_window_mining_report,
    mine_fixed_windows,
    write_window_mining_report,
)
from pm_bot.strategies.crypto.phase1.window_report import (
    CryptoFamilyExportResult,
    CryptoWindowFamilyReport,
    export_crypto_family_window,
    format_crypto_family_export_result,
    format_crypto_window_family_report,
    generate_crypto_window_family_report,
    write_crypto_family_export_result,
    write_crypto_window_family_report,
)
from pm_bot.strategies.crypto.phase1.signal_report import (
    CryptoSignalReport,
    format_crypto_signal_report,
    generate_crypto_signal_report,
    write_crypto_signal_report,
)

__all__ = [
    "AutoresearchReport",
    "CryptoFamilyExportResult",
    "CryptoSignalReport",
    "CryptoWindowFamilyReport",
    "FixedWindowExperimentReport",
    "PaperIntegrityReport",
    "Phase1ReplayResult",
    "ReplayDeterminismReport",
    "ResearchRunResult",
    "WindowMiningReport",
    "format_autoresearch_report",
    "export_crypto_family_window",
    "format_crypto_family_export_result",
    "format_crypto_signal_report",
    "format_crypto_window_family_report",
    "format_fixed_window_report",
    "format_phase1_replay_result",
    "format_paper_integrity_report",
    "format_replay_determinism_report",
    "generate_autoresearch_report",
    "generate_crypto_signal_report",
    "generate_crypto_window_family_report",
    "generate_paper_integrity_report",
    "generate_replay_determinism_report",
    "default_phase1_config_dir",
    "format_research_summary",
    "format_window_mining_report",
    "load_market_snapshots",
    "mine_fixed_windows",
    "run_backtest",
    "run_fixed_window_experiments",
    "run_phase1_replay",
    "run_replay",
    "run_replay_snapshots",
    "write_autoresearch_report",
    "write_crypto_signal_report",
    "write_crypto_window_family_report",
    "write_crypto_family_export_result",
    "write_fixed_window_report",
    "write_paper_integrity_report",
    "write_replay_determinism_report",
    "write_window_mining_report",
]
