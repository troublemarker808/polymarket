from __future__ import annotations

from pathlib import Path

from pm_bot.strategies.crypto.phase2.preset_rollback import rollback_crypto_phase2_preset_application


def test_rollback_crypto_phase2_preset_application_restores_backup(tmp_path: Path) -> None:
    backup_path = tmp_path / "crypto.applied.backup.toml"
    target_path = tmp_path / "crypto.v1.toml"
    output_path = tmp_path / "crypto.rolledback.toml"
    backup_path.write_text(
        '\n'.join(
            [
                'category = "crypto"',
                "",
                "[strategy.phase2]",
                'min_confidence = 0.6',
                "",
                "[strategy.phase2.preset_registry.baseline.match]",
                'underlying = "BTC"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = rollback_crypto_phase2_preset_application(
        backup_config_path=backup_path,
        target_config_path=target_path,
        output_config_path=output_path,
    )

    assert result.rolled_back is True
    assert output_path.exists()
    assert result.restored_preset_names == ("baseline",)


def test_rollback_crypto_phase2_preset_application_blocks_missing_backup(tmp_path: Path) -> None:
    result = rollback_crypto_phase2_preset_application(
        backup_config_path=tmp_path / "missing.backup.toml",
        target_config_path=tmp_path / "crypto.v1.toml",
    )

    assert result.rolled_back is False
    assert "backup config path does not exist" in result.blockers
