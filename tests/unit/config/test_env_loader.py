from pathlib import Path
import os

from pm_bot.config.env import load_local_env


def test_load_local_env_reads_env_file_without_overriding_existing_values(
    tmp_path: Path,
    monkeypatch,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "PM_BOT_TEST_NEW=value-from-dotenv",
                "PM_BOT_TEST_EXISTING=value-from-dotenv",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PM_BOT_TEST_NEW", raising=False)
    monkeypatch.setenv("PM_BOT_TEST_EXISTING", "already-set")

    load_local_env()

    assert os.getenv("PM_BOT_TEST_NEW") == "value-from-dotenv"
    assert os.getenv("PM_BOT_TEST_EXISTING") == "already-set"
