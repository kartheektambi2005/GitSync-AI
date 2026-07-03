from pathlib import Path

from config_manager import AgentConfig, ConfigManager, FolderMapping


def test_config_manager_creates_default_config(tmp_path: Path):
    cm = ConfigManager(config_dir=tmp_path, fmt="yaml")
    cfg = cm.load()
    assert isinstance(cfg, AgentConfig)
    assert cfg.mappings == {}
    assert (tmp_path / "config.yaml").exists()


def test_config_manager_json_roundtrip(tmp_path: Path):
    cm = ConfigManager(config_dir=tmp_path, fmt="json")
    mapping = FolderMapping(
        folder_path=str(tmp_path / "proj"),
        remote_url="https://github.com/user/repo.git",
        project_type="Python",
    )
    cm.update_mapping(mapping)

    cm2 = ConfigManager(config_dir=tmp_path, fmt="json")
    cfg2 = cm2.load()
    saved = cfg2.get_mapping(str(tmp_path / "proj"))
    assert saved is not None
    assert saved.remote_url == "https://github.com/user/repo.git"
    assert saved.project_type == "Python"


def test_folder_mapping_path_normalization(tmp_path: Path):
    mapping = FolderMapping(
        folder_path=str(tmp_path) + "/./",
        remote_url="https://github.com/user/repo.git",
    )
    assert mapping.folder_path == str(tmp_path.resolve())
