"""Controlled rollback for crypto phase2 preset applications."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import tomllib
from typing import Any


@dataclass(slots=True, frozen=True)
class CryptoPhase2PresetRollbackResult:
    rolled_back: bool
    source_backup_path: str
    target_config_path: str
    output_config_path: str
    restored_preset_names: tuple[str, ...]
    blockers: tuple[str, ...]


def rollback_crypto_phase2_preset_application(
    *,
    backup_config_path: str | Path,
    target_config_path: str | Path,
    output_config_path: str | Path | None = None,
) -> CryptoPhase2PresetRollbackResult:
    backup_path = Path(backup_config_path)
    target_path = Path(target_config_path)
    output_path = Path(output_config_path) if output_config_path is not None else target_path.with_name(
        f"{target_path.stem}.rolledback{target_path.suffix}"
    )

    blockers: list[str] = []
    if not backup_path.exists():
        blockers.append("backup config path does not exist")

    if blockers:
        return CryptoPhase2PresetRollbackResult(
            rolled_back=False,
            source_backup_path=str(backup_path),
            target_config_path=str(target_path),
            output_config_path=str(output_path),
            restored_preset_names=(),
            blockers=tuple(blockers),
        )

    restored_text = backup_path.read_text(encoding="utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(restored_text, encoding="utf-8")
    restored_preset_names = _load_restored_preset_names(output_path)
    return CryptoPhase2PresetRollbackResult(
        rolled_back=True,
        source_backup_path=str(backup_path),
        target_config_path=str(target_path),
        output_config_path=str(output_path),
        restored_preset_names=restored_preset_names,
        blockers=(),
    )


def format_crypto_phase2_preset_rollback_result(
    result: CryptoPhase2PresetRollbackResult,
) -> str:
    lines = [
        "# Crypto Phase 2 Preset Rollback Result",
        "",
        f"- rolled_back: {str(result.rolled_back).lower()}",
        f"- source_backup_path: {result.source_backup_path}",
        f"- target_config_path: {result.target_config_path}",
        f"- output_config_path: {result.output_config_path}",
        f"- restored_preset_names: {', '.join(result.restored_preset_names) if result.restored_preset_names else 'none'}",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {blocker}" for blocker in result.blockers or ("none",))
    return "\n".join(lines) + "\n"


def write_crypto_phase2_preset_rollback_result(
    *,
    result: CryptoPhase2PresetRollbackResult,
    output_path: str | Path,
) -> None:
    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        format_crypto_phase2_preset_rollback_result(result),
        encoding="utf-8",
    )
    target_path.with_suffix(".json").write_text(
        json.dumps(_normalize(asdict(result)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _load_restored_preset_names(path: Path) -> tuple[str, ...]:
    try:
        with path.open("rb") as handle:
            decoded = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return ()
    strategy = decoded.get("strategy", {})
    if not isinstance(strategy, dict):
        return ()
    phase2 = strategy.get("phase2", {})
    if not isinstance(phase2, dict):
        return ()
    preset_registry = phase2.get("preset_registry", {})
    if not isinstance(preset_registry, dict):
        return ()
    return tuple(str(name) for name in preset_registry.keys())


def _normalize(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    return value
