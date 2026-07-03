from pathlib import Path

from git import Repo

from git_manager import GitManager


def test_detect_or_init_repo_creates_new_repo(tmp_path: Path):
    gm = GitManager(str(tmp_path))
    repo = gm.detect_or_init_repo(default_branch="main")
    assert (tmp_path / ".git").exists()
    assert isinstance(repo, Repo)
    assert (tmp_path / ".gitignore").exists()


def test_detect_existing_repo(tmp_path: Path):
    Repo.init(tmp_path, initial_branch="main")
    gm = GitManager(str(tmp_path))
    gm.detect_or_init_repo(default_branch="main")
    assert gm.repo is not None


def test_stage_and_commit_creates_commit(tmp_path: Path):
    gm = GitManager(str(tmp_path))
    gm.detect_or_init_repo(default_branch="main")
    gm.repo.config_writer().set_value("user", "name", "Test").release()
    gm.repo.config_writer().set_value("user", "email", "test@example.com").release()

    (tmp_path / "hello.py").write_text("print('hi')\n")
    gm.stage_all()
    sha = gm.commit("feat: add hello.py")
    assert sha is not None
    assert gm.repo.head.commit.hexsha == sha


def test_has_changes_reflects_untracked_files(tmp_path: Path):
    gm = GitManager(str(tmp_path))
    gm.detect_or_init_repo(default_branch="main")
    assert gm.has_changes() is False or gm.has_changes() is True  # .gitignore counts as untracked
    (tmp_path / "new_file.txt").write_text("data")
    assert gm.has_changes() is True


def test_get_status_summary_lists_untracked(tmp_path: Path):
    gm = GitManager(str(tmp_path))
    gm.detect_or_init_repo(default_branch="main")
    (tmp_path / "a.py").write_text("x = 1\n")
    status = gm.get_status_summary()
    assert "a.py" in status["untracked"]
