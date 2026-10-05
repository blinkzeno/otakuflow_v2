"""Path guards: escapes are rejected, layout is created."""

import pytest

from backend.storage import paths


def test_parent_escape_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    with pytest.raises(ValueError):
        paths.safe_join("projects", "..", "evil")


def test_absolute_part_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    with pytest.raises(ValueError):
        paths.safe_join("C:\\Windows\\evil")


def test_normal_path_stays_inside_root(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    resolved = paths.safe_join("projects", "1", "pages", "p_0001.jpg")
    assert resolved.is_relative_to(paths.data_root())


def test_project_layout_created(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    base = paths.ensure_project_dirs(7)
    for sub in ("originals", "pages", "thumbs", "audio", "renders", "logs", "tmp"):
        assert (base / sub).is_dir()


def test_data_root_anchored_to_repo(tmp_path, monkeypatch):
    from backend.core import config

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATA_DIR", "./data")
    assert paths.data_root() == config.repo_root() / "data"
