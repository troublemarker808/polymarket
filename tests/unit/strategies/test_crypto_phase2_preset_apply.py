from __future__ import annotations

import json
from pathlib import Path

from pm_bot.strategies.crypto.phase2.preset_apply import apply_crypto_phase2_preset_change_package


def test_apply_crypto_phase2_preset_change_package_writes_applied_config(tmp_path: Path) -> None:
    package_path = tmp_path / "change-package.json"
    target_path = tmp_path / "crypto.v1.toml"
    output_path = tmp_path / "crypto.applied.toml"
    package_path.write_text(
        json.dumps(
            {
                "ready_to_apply": True,
                "patch": {
                    "execution_faster_quotes": {
                        "match": {"underlying": "ETH", "event_family": "dip"},
                        "overrides": {"maker_quote_ttl_seconds": 45},
                        "rationale": ["reduce expiration pressure"],
                        "focus": "execution",
                    }
                },
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    target_path.write_text(
        'category = "crypto"\n\n[strategy.phase2]\nmin_confidence = 0.6\n',
        encoding="utf-8",
    )

    result = apply_crypto_phase2_preset_change_package(
        change_package_path=package_path,
        target_config_path=target_path,
        output_config_path=output_path,
    )

    assert result.applied is True
    assert result.next_working_preset == "unknown"
    assert result.verification_steps
    assert result.rollback_steps
    assert output_path.exists()
    rendered = output_path.read_text(encoding="utf-8")
    assert "[strategy.phase2.preset_registry.execution_faster_quotes.match]" in rendered
    assert 'underlying = "ETH"' in rendered
    assert output_path.with_name("crypto.applied.backup.toml").exists()
    assert result.rollback_output_config_path.endswith("crypto.applied.rollback.toml")
