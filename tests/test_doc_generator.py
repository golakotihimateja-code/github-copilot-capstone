import pytest

from src.doc_generator import generate_markdown


def test_generates_module_function_class_and_method_docs(tmp_path):
	source_dir = tmp_path / "source"
	source_dir.mkdir()
	(source_dir / "api.py").write_text(
		'"""Public API module."""\n'
		'def greet(name: str) -> str:\n'
		'    """Return a greeting."""\n'
		'    return f"Hello, {name}"\n\n'
		'class Greeter:\n'
		'    """Greets people."""\n'
		'    def greet(self, name: str) -> str:\n'
		'        """Return a personalized greeting."""\n'
		'        return name\n',
		encoding="utf-8",
	)

	markdown = generate_markdown(source_dir)

	assert "## Module: `api.py`" in markdown
	assert "Public API module." in markdown
	assert "Function: `def greet(name: str) -> str`" in markdown
	assert "Class: `Greeter`" in markdown
	assert "Method: `def greet(self, name: str) -> str`" in markdown


def test_writes_markdown_and_skips_hidden_or_environment_directories(tmp_path):
	source_dir = tmp_path / "source"
	(source_dir / "pkg").mkdir(parents=True)
	(source_dir / ".hidden").mkdir()
	(source_dir / ".venv" / "Lib").mkdir(parents=True)
	(source_dir / "pkg" / "visible.py").write_text("value = 1\n", encoding="utf-8")
	(source_dir / ".hidden" / "hidden.py").write_text("hidden = True\n", encoding="utf-8")
	(source_dir / ".venv" / "Lib" / "environment.py").write_text(
		"environment = True\n", encoding="utf-8"
	)
	output_file = tmp_path / "docs" / "reference.md"

	markdown = generate_markdown(source_dir, output_file)

	assert output_file.read_text(encoding="utf-8") == markdown
	assert "pkg/visible.py" in markdown
	assert "hidden.py" not in markdown
	assert "environment.py" not in markdown


def test_does_not_execute_scanned_source(tmp_path):
	source_dir = tmp_path / "source"
	source_dir.mkdir()
	(source_dir / "unsafe.py").write_text(
		'raise RuntimeError("source must not execute")\n', encoding="utf-8"
	)

	markdown = generate_markdown(source_dir)

	assert "unsafe.py" in markdown
	assert "RuntimeError" not in markdown


def test_invalid_python_fails_without_writing_partial_output(tmp_path):
	source_dir = tmp_path / "source"
	source_dir.mkdir()
	(source_dir / "invalid.py").write_text("def broken(:\n", encoding="utf-8")
	output_file = tmp_path / "reference.md"

	with pytest.raises(SyntaxError):
		generate_markdown(source_dir, output_file)

	assert not output_file.exists()


def test_missing_source_directory_is_rejected(tmp_path):
	with pytest.raises(NotADirectoryError):
		generate_markdown(tmp_path / "missing")


def test_documents_async_functions_and_omits_private_definitions(tmp_path):
	source_dir = tmp_path / "source"
	source_dir.mkdir()
	(source_dir / "api.py").write_text(
		'async def fetch_data(url: str) -> bytes:\n'
		'    """Fetch data from a URL."""\n'
		'    return b""\n\n'
		'def _internal_helper() -> None:\n'
		'    """Internal helper."""\n'
		'    return None\n\n'
		'class Client:\n'
		'    def _hidden_method(self) -> None:\n'
		'        """Hidden method."""\n'
		'        return None\n',
		encoding="utf-8",
	)

	markdown = generate_markdown(source_dir)

	assert "async def fetch_data(url: str) -> bytes" in markdown
	assert "Fetch data from a URL." in markdown
	assert "_internal_helper" not in markdown
	assert "_hidden_method" not in markdown


def test_empty_source_directory_returns_valid_markdown(tmp_path):
	source_dir = tmp_path / "source"
	source_dir.mkdir()

	markdown = generate_markdown(source_dir)

	assert markdown.startswith("# Generated Source Documentation\n")
	assert "_No Python source files were found._" in markdown
