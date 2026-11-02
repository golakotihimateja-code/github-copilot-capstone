import logging

import pytest

from src.notifier import MockNotifier
from src.sync_service import DocumentationSyncService


def test_source_change_generates_docs_notifies_and_logs(tmp_path, caplog):
	source_dir = tmp_path / "source"
	source_dir.mkdir()
	source_file = source_dir / "module.py"
	source_file.write_text('"""Initial module."""\n', encoding="utf-8")
	output_file = tmp_path / "docs" / "reference.md"
	notifier = MockNotifier()
	service = DocumentationSyncService(
		source_dir, output_file, "org/repo", ["dev@example.com"], notifier
	)

	with caplog.at_level(logging.INFO):
		assert service.run_once() is False
		source_file.write_text('"""Updated module."""\n', encoding="utf-8")
		assert service.run_once() is True

	assert "Updated module." in output_file.read_text(encoding="utf-8")
	assert len(notifier.sent_notifications) == 1
	assert notifier.sent_notifications[0].recipient == "dev@example.com"
	assert "Source changes detected" in caplog.text
	assert "Documentation synchronized successfully" in caplog.text


def test_unchanged_sources_do_not_regenerate_or_notify(tmp_path):
	source_dir = tmp_path / "source"
	source_dir.mkdir()
	(source_dir / "module.py").write_text("value = 1\n", encoding="utf-8")
	notifier = MockNotifier()
	service = DocumentationSyncService(
		source_dir, tmp_path / "reference.md", "org/repo", ["dev@example.com"], notifier
	)

	assert service.run_once() is False
	assert service.run_once() is False
	assert notifier.sent_notifications == []


def test_failed_generation_is_logged_and_retried_after_fix(tmp_path, caplog):
	source_dir = tmp_path / "source"
	source_dir.mkdir()
	source_file = source_dir / "module.py"
	source_file.write_text("value = 1\n", encoding="utf-8")
	notifier = MockNotifier()
	service = DocumentationSyncService(
		source_dir, tmp_path / "reference.md", "org/repo", ["dev@example.com"], notifier
	)
	service.run_once()
	source_file.write_text("def invalid(:\n", encoding="utf-8")

	with caplog.at_level(logging.ERROR):
		assert service.run_once() is False

	assert "Documentation synchronization failed" in caplog.text
	assert notifier.sent_notifications == []

	source_file.write_text('"""Fixed module."""\n', encoding="utf-8")
	assert service.run_once() is True
	assert len(notifier.sent_notifications) == 1


def test_detects_created_and_deleted_source_files(tmp_path):
	source_dir = tmp_path / "source"
	source_dir.mkdir()
	(source_dir / "initial.py").write_text('"""Initial."""\n', encoding="utf-8")
	output_file = tmp_path / "reference.md"
	notifier = MockNotifier()
	service = DocumentationSyncService(
		source_dir, output_file, "org/repo", ["dev@example.com"], notifier
	)
	assert service.run_once() is False

	created_file = source_dir / "added.py"
	created_file.write_text('"""Added module."""\n', encoding="utf-8")
	assert service.run_once() is True
	assert "Added module." in output_file.read_text(encoding="utf-8")

	created_file.unlink()
	assert service.run_once() is True
	assert "Added module." not in output_file.read_text(encoding="utf-8")
	assert len(notifier.sent_notifications) == 2


def test_ignores_non_python_file_changes(tmp_path):
	source_dir = tmp_path / "source"
	source_dir.mkdir()
	(source_dir / "module.py").write_text("value = 1\n", encoding="utf-8")
	service = DocumentationSyncService(
		source_dir, tmp_path / "reference.md", "org/repo", []
	)
	assert service.run_once() is False

	(source_dir / "notes.txt").write_text("not Python source", encoding="utf-8")

	assert service.run_once() is False


@pytest.mark.parametrize("poll_interval", [0, -1])
def test_watch_rejects_nonpositive_poll_interval(tmp_path, poll_interval):
	source_dir = tmp_path / "source"
	source_dir.mkdir()
	service = DocumentationSyncService(
		source_dir, tmp_path / "reference.md", "org/repo", []
	)

	with pytest.raises(ValueError, match="poll_interval"):
		service.watch(poll_interval)
