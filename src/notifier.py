"""Mock notification adapter for documentation updates."""

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Notification:
	"""An email-shaped notification captured by the mock notifier."""

	recipient: str
	subject: str
	body: str


class MockNotifier:
	"""Record notifications in memory instead of sending real email."""

	def __init__(self) -> None:
		self.sent_notifications: list[Notification] = []

	def notify_documentation_updated(
		self,
		recipients: Iterable[str],
		repository: str,
		documentation_path: str,
	) -> list[Notification]:
		"""Create and record one update notification for each recipient."""
		if not repository.strip():
			raise ValueError("repository must not be empty")
		if not documentation_path.strip():
			raise ValueError("documentation_path must not be empty")

		notifications = [
			Notification(
				recipient=recipient,
				subject=f"Documentation updated: {repository}",
				body=(
					f"Documentation was updated in {repository}.\n"
					f"Updated file: {documentation_path}"
				),
			)
			for recipient in recipients
			if recipient.strip()
		]
		self.sent_notifications.extend(notifications)
		return notifications
