"""The scaffolded cloud-setup.sh follows the hub's Drive MCP change (library#48, notes-wiki#383).

The script only runs in a cloud session, so these read it: it installs `gwscli`, documents
`GDRIVE_SA_JSON` as the drive.readonly user grant, and writes the converter's key.
"""

from __future__ import annotations

from linkage import scaffold

SCRIPT = (scaffold.scaffold_dir() / "claude" / "cloud-setup.sh").read_text(encoding="utf-8")


def test_the_script_installs_gwscli_and_the_fast_path_waits_for_it():
    assert "https://dl.google.com/workspace-cli/install.sh" in SCRIPT
    assert "GWSCLI_INSTALL_DIR=/usr/local/bin" in SCRIPT
    assert "command -v gwscli" in SCRIPT


def test_gdrive_sa_json_is_documented_as_the_read_grant():
    assert "authorized_user" in SCRIPT
    assert "queue-gdrive-agent-oauth-ro" in SCRIPT
    assert "read-only Google service-account JSON" not in SCRIPT


def test_the_converter_key_is_written_and_named_in_the_config():
    assert "LIBRARY_CONVERT_KEY_JSON" in SCRIPT
    assert "$CFG_DIR/convert-sa.json" in SCRIPT
    assert 'cfg["convert_credentials"]' in SCRIPT
