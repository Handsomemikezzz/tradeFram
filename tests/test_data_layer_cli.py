from __future__ import annotations

import subprocess
import sys


def test_init_history_data_cli_help_lists_sync_flags():
    result = subprocess.run([sys.executable, "scripts/init_history_data.py", "--help"], capture_output=True, text=True)

    assert result.returncode == 0
    assert "--start-date" in result.stdout
    assert "--data-root" in result.stdout
    assert "--update-business-cache" in result.stdout


def test_sync_daily_data_cli_help_lists_sync_flags():
    result = subprocess.run([sys.executable, "scripts/sync_daily_data.py", "--help"], capture_output=True, text=True)

    assert result.returncode == 0
    assert "--lookback-days" in result.stdout
    assert "--retry-failed" in result.stdout
    assert "--dry-run" in result.stdout
