"""Controlled application of weather preset change packages."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import tomllib
from typing import Any


@dataclass(slots=True, frozen=True)
class WeatherPresetApplyResult:
    ready_to_apply: bool
    applied: bool
    next_working_preset: str
    source_package_path: str
    target_config_path: str
    output_config_path: str
    backup_config_path: str
    rollback_output_config_path: str
    applied_preset_names: tuple[str, ...]
    verification_steps: tuple[str, ...]
    rollback_steps: tuple[str, ...]
    blockers: tuple[str, ...]


def apply_weather_preset_change_package(
    *,
    change_package_path: str | Path,
    target_config_path: str | Path,
    output_config_path: str | Path | None = None,
) -> WeatherPresetApplyResult:
    package_path = Path(change_package_path)
    target_path = Path(target_config_path)
    decoded = json.loads(package_path.read_text(encoding="utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError("weather preset change package must be a JSON object")

    ready_to_apply = bool(decoded.get("ready_to_apply", False))
    next_working_preset = str(decoded.get("next_working_preset", "unknown")).strip() or "unknown"
    patch = decoded.get("patch", {})
    blockers: list[str] = []
    if not ready_to_apply:
        blockers.append("weather change package is not ready_to_apply")
    if not isinstance(patch, dict) or not patch:
        blockers.append("weather change package patch is empty")

    output_path = Path(output_config_path) if output_config_path is not None else target_path.with_name(
        f"{target_path.stem}.applied{target_path.suffix}"
    )
    backup_path = output_path.with_name(f"{output_path.stem}.backup{target_path.suffix}")
    rollback_output_path = output_path.with_name(f"{output_path.stem}.rollback{target_path.suffix}")
    verification_steps = _build_verification_steps(
        next_working_preset=next_working_preset,
        output_path=output_path,
        backup_path=backup_path,
    )
    rollback_steps = _build_rollback_steps(
        backup_path=backup_path,
        output_path=output_path,
        rollback_output_path=rollback_output_path,
    )

    if blockers:
        return WeatherPresetApplyResult(
            ready_to_apply=ready_to_apply,
            applied=False,
            next_working_preset=next_working_preset,
            source_package_path=str(package_path),
            target_config_path=str(target_path),
            output_config_path=str(output_path),
            backup_config_path=str(backup_path),
            rollback_output_config_path=str(rollback_output_path),
            applied_preset_names=(),
            verification_steps=verification_steps,
            rollback_steps=rollback_steps,
            blockers=tuple(blockers),
        )

    config = _load_toml_document(target_path)
    threshold_registry = _resolve_registry(config, ("strategy", "threshold", "preset_registry"))
    ensemble_registry = _resolve_registry(config, ("strategy", "ensemble", "preset_registry"))
    for preset_name, preset_payload in patch.items():
        if isinstance(preset_name, str) and isinstance(preset_payload, dict):
            threshold_registry[preset_name] = preset_payload
            ensemble_registry[preset_name] = preset_payload

    output_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path.write_text(target_path.read_text(encoding="utf-8"), encoding="utf-8")
    output_path.write_text(_render_toml(config), encoding="utf-8")
    return WeatherPresetApplyResult(
        ready_to_apply=ready_to_apply,
        applied=True,
        next_working_preset=next_working_preset,
        source_package_path=str(package_path),
        target_config_path=str(target_path),
        output_config_path=str(output_path),
        backup_config_path=str(backup_path),
        rollback_output_config_path=str(rollback_output_path),
        applied_preset_names=tuple(str(name) for name in patch.keys()),
        verification_steps=verification_steps,
        rollback_steps=rollback_steps,
        blockers=(),
    )


def format_weather_preset_apply_result(result: WeatherPresetApplyResult) -> str:
    lines = [
        "# Weather Preset Apply Result",
        "",
        f"- ready_to_apply: {str(result.ready_to_apply).lower()}",
        f"- applied: {str(result.applied).lower()}",
        f"- next_working_preset: {result.next_working_preset}",
        f"- source_package_path: {result.source_package_path}",
        f"- target_config_path: {result.target_config_path}",
        f"- output_config_path: {result.output_config_path}",
        f"- backup_config_path: {result.backup_config_path}",
        f"- rollback_output_config_path: {result.rollback_output_config_path}",
        f"- applied_preset_names: {', '.join(result.applied_preset_names) if result.applied_preset_names else 'none'}",
        "",
        "## Verification Steps",
        "",
    ]
    lines.extend(f"- {step}" for step in result.verification_steps)
    lines.extend(["", "## Rollback Steps", ""])
    lines.extend(f"- {step}" for step in result.rollback_steps)
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}" for blocker in result.blockers or ("none",))
    return "\n".join(lines) + "\n"


def write_weather_preset_apply_result(
    *,
    result: WeatherPresetApplyResult,
    output_path: str | Path,
) -> None:
    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        format_weather_preset_apply_result(result),
        encoding="utf-8",
    )
    target_path.with_suffix(".json").write_text(
        json.dumps(_normalize(asdict(result)), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _load_toml_document(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        decoded = tomllib.load(handle)
    if isinstance(decoded, dict):
        return decoded
    raise ValueError("target config must decode to a mapping")


def _resolve_registry(document: dict[str, Any], path: tuple[str, ...]) -> dict[str, Any]:
    current: dict[str, Any] = document
    for key in path:
        child = current.setdefault(key, {})
        if not isinstance(child, dict):
            child = {}
            current[key] = child
        current = child
    return current


def _render_toml(document: dict[str, Any]) -> str:
    scalar_lines: list[str] = []
    table_lines: list[str] = []
    _render_section(document, (), scalar_lines, table_lines)
    rendered = scalar_lines[:]
    if scalar_lines and table_lines:
        rendered.append("")
    rendered.extend(table_lines)
    return "\n".join(rendered).rstrip() + "\n"


def _render_section(value: dict[str, Any], prefix: tuple[str, ...], scalar_lines: list[str], table_lines: list[str]) -> None:
    scalar_items: list[tuple[str, Any]] = []
    nested_items: list[tuple[str, dict[str, Any]]] = []
    for key, item in value.items():
        if isinstance(item, dict):
            nested_items.append((str(key), item))
        else:
            scalar_items.append((str(key), item))
    if prefix:
        table_lines.append(f"[{'.'.join(prefix)}]")
    target_lines = table_lines if prefix else scalar_lines
    for key, item in scalar_items:
        target_lines.append(f"{key} = {_render_value(item)}")
    if prefix and (scalar_items or nested_items):
        table_lines.append("")
    for index, (key, nested) in enumerate(nested_items):
        _render_section(nested, prefix + (key,), scalar_lines, table_lines)
        if index != len(nested_items) - 1:
            table_lines.append("")


def _render_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(_render_value(item) for item in value) + "]"
    if value is None:
        return '""'
    return _render_value(str(value))


def _build_verification_steps(*, next_working_preset: str, output_path: Path, backup_path: Path) -> tuple[str, ...]:
    return (
        f"review the rendered config diff between {backup_path.name} and {output_path.name}",
        f"run a fresh weather replay using {output_path.name} and confirm {next_working_preset} still produces proceed-grade results",
        "compare readiness_score and total_profit_loss against the previous weather working preset window",
        "only promote the applied config into a broader weather profile after the verification replay remains stable",
    )


def _build_rollback_steps(*, backup_path: Path, output_path: Path, rollback_output_path: Path) -> tuple[str, ...]:
    return (
        f"if post-apply verification regresses, restore {backup_path.name} into {rollback_output_path.name}",
        f"treat {output_path.name} as candidate-only until the rollback decision is cleared",
        "re-run the previous weather working preset verification replay before re-attempting promotion",
    )


def _normalize(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    return value
