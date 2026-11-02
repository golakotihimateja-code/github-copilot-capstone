"""Poll Python source files and synchronize generated documentation."""

import argparse
import logging
from pathlib import Path
from threading import Event
from typing import Dict, Iterable, Optional, Tuple

from src.doc_generator import generate_markdown
from src.notifier import MockNotifier

logger = logging.getLogger(__name__)

FileState = Tuple[int, int]


class DocumentationSyncService:
	"""Detect source changes and run documentation generation and notification."""

	def __init__(
		self,
		source_dir: Path,
		output_file: Path,
		repository: str,
		recipients: Iterable[str],
		notifier: Optional[MockNotifier] = None,
	) -> None:
		self.source_dir = Path(source_dir)
		self.output_file = Path(output_file)
		self.repository = repository
		self.recipients = tuple(recipients)
		self.notifier = notifier or MockNotifier()
		self._previous_state: Optional[Dict[Path, FileState]] = None

		if not self.source_dir.is_dir():
			raise NotADirectoryError(f"Source directory does not exist: {self.source_dir}")
		if not repository.strip():
			raise ValueError("repository must not be empty")

	def _snapshot(self) -> Dict[Path, FileState]:
		snapshot: Dict[Path, FileState] = {}
		for path in self.source_dir.rglob("*.py"):
			relative_parts = path.relative_to(self.source_dir).parts[:-1]
			if any(part.startswith(".") or part in {"venv", "__pycache__", "node_modules"} for part in relative_parts):
				continue
			try:
				stat = path.stat()
			except FileNotFoundError:
				continue
			snapshot[path] = (stat.st_mtime_ns, stat.st_size)
		return snapshot

	def run_once(self) -> bool:
		"""Check for source changes; return true when synchronization succeeds."""
		current_state = self._snapshot()
		if self._previous_state is None:
			self._previous_state = current_state
			logger.info("Initialized source snapshot for %s", self.source_dir)
			return False
		if current_state == self._previous_state:
			return False

		changed_paths = sorted(
			path
			for path in self._previous_state.keys() | current_state.keys()
			if self._previous_state.get(path) != current_state.get(path)
		)
		logger.info("Source changes detected: %s", ", ".join(map(str, changed_paths)))

		try:
			generate_markdown(self.source_dir, self.output_file)
			self.notifier.notify_documentation_updated(
				self.recipients,
				self.repository,
				self.output_file.as_posix(),
			)
		except Exception:
			logger.exception("Documentation synchronization failed")
			return False

		self._previous_state = current_state
		logger.info("Documentation synchronized successfully: %s", self.output_file)
		return True

	def watch(self, poll_interval: float = 1.0, stop_event: Optional[Event] = None) -> None:
		"""Poll until stopped; the first poll establishes the baseline snapshot."""
		if poll_interval <= 0:
			raise ValueError("poll_interval must be greater than zero")

		stop = stop_event or Event()
		logger.info("Watching Python source under %s", self.source_dir)
		while not stop.is_set():
			self.run_once()
			stop.wait(poll_interval)


def main() -> int:
	parser = argparse.ArgumentParser(
		description="Watch Python source files and synchronize generated documentation."
	)
	parser.add_argument("source_dir", type=Path, help="Directory containing Python source")
	parser.add_argument("output_file", type=Path, help="Path for generated Markdown")
	parser.add_argument("--repository", required=True, help="Repository name, e.g. org/project")
	parser.add_argument(
		"--recipient", action="append", default=[], help="Notification recipient (repeatable)"
	)
	parser.add_argument("--poll-interval", type=float, default=1.0)
	arguments = parser.parse_args()

	logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
	service = DocumentationSyncService(
		arguments.source_dir,
		arguments.output_file,
		arguments.repository,
		arguments.recipient,
	)
	try:
		service.watch(arguments.poll_interval)
	except KeyboardInterrupt:
		logger.info("Documentation watcher stopped")
	except (OSError, ValueError) as error:
		logger.error("Unable to start documentation watcher: %s", error)
		return 1
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
