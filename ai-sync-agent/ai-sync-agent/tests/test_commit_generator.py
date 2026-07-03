from commit_generator import CommitGenerator


def test_no_changes_returns_generic_message():
    gen = CommitGenerator()
    msg = gen.generate({"added": [], "modified": [], "deleted": [], "untracked": []})
    assert "sync" in msg.lower()


def test_added_files_uses_feat_prefix():
    gen = CommitGenerator()
    msg = gen.generate(
        {"added": [], "modified": [], "deleted": [], "untracked": ["main.py", "utils.py"]}
    )
    assert msg.startswith("feat:")
    assert "2 file(s)" in msg
    assert "Python" in msg


def test_modified_only_uses_fix_prefix():
    gen = CommitGenerator()
    msg = gen.generate(
        {"added": [], "modified": ["app.js"], "deleted": [], "untracked": []}
    )
    assert msg.startswith("fix:")


def test_mixed_changes_uses_chore_prefix_and_detail_lines():
    gen = CommitGenerator()
    msg = gen.generate(
        {
            "added": [],
            "modified": ["index.html"],
            "deleted": ["old.css"],
            "untracked": ["new_component.jsx"],
        }
    )
    assert msg.startswith("chore:")
    assert "Added:" in msg
    assert "Modified:" in msg
    assert "Deleted:" in msg


def test_detail_line_truncates_long_lists():
    gen = CommitGenerator()
    files = [f"file_{i}.py" for i in range(10)]
    msg = gen.generate({"added": [], "modified": files, "deleted": [], "untracked": []})
    assert "+5 more" in msg
