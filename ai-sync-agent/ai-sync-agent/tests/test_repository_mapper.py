from pathlib import Path

from config_manager import ConfigManager
from repository_mapper import RepositoryMapper, is_valid_github_url


def test_valid_github_urls():
    assert is_valid_github_url("https://github.com/user/repo.git")
    assert is_valid_github_url("https://github.com/user/repo")
    assert is_valid_github_url("git@github.com:user/repo.git")
    assert not is_valid_github_url("not a url")
    assert not is_valid_github_url("https://gitlab.com/user/repo.git")


def test_ensure_mapping_prompts_once_then_persists(tmp_path: Path):
    cm = ConfigManager(config_dir=tmp_path, fmt="yaml")
    mapper = RepositoryMapper(cm)

    prompts = []

    def fake_prompt(msg: str) -> str:
        prompts.append(msg)
        return "https://github.com/user/repo.git"

    project_dir = tmp_path / "myproject"
    project_dir.mkdir()

    mapping1 = mapper.ensure_mapping(str(project_dir), project_type="Python", prompt_fn=fake_prompt)
    assert mapping1.remote_url == "https://github.com/user/repo.git"
    assert len(prompts) == 1

    # Second call should NOT prompt again
    mapping2 = mapper.ensure_mapping(str(project_dir), project_type="Python", prompt_fn=fake_prompt)
    assert mapping2.remote_url == "https://github.com/user/repo.git"
    assert len(prompts) == 1
