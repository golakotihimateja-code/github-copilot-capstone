import pytest

from src.notifier import MockNotifier


def test_records_documentation_update_for_each_recipient():
	notifier = MockNotifier()

	notifications = notifier.notify_documentation_updated(
		["dev@example.com", "reviewer@example.com"],
		"acme/project",
		"docs/api.md",
	)

	assert notifications == notifier.sent_notifications
	assert [item.recipient for item in notifications] == [
		"dev@example.com",
		"reviewer@example.com",
	]
	assert all(item.subject == "Documentation updated: acme/project" for item in notifications)
	assert all("Updated file: docs/api.md" in item.body for item in notifications)


def test_ignores_blank_recipients():
	notifier = MockNotifier()

	notifications = notifier.notify_documentation_updated(
		["dev@example.com", "  "], "acme/project", "docs/api.md"
	)

	assert len(notifications) == 1
	assert notifications[0].recipient == "dev@example.com"


def test_empty_recipient_list_sends_nothing():
	notifier = MockNotifier()

	notifications = notifier.notify_documentation_updated(
		[], "acme/project", "docs/api.md"
	)

	assert notifications == []
	assert notifier.sent_notifications == []


@pytest.mark.parametrize(
	("repository", "documentation_path"),
	[("", "docs/api.md"), ("acme/project", "  ")],
)
def test_rejects_missing_update_details(repository, documentation_path):
	notifier = MockNotifier()

	with pytest.raises(ValueError):
		notifier.notify_documentation_updated(
			["dev@example.com"], repository, documentation_path
		)
