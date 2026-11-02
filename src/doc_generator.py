"""Generate Markdown reference documentation from Python source files."""

import argparse
import ast
from pathlib import Path
import sys
import textwrap
from typing import Optional, Union

PathLike = Union[str, Path]

_SKIP_DIRECTORY_NAMES = {".git", ".venv", "venv", "__pycache__", "node_modules"}


def _python_files(source_dir: Path) -> list[Path]:
	return sorted(
		path
		for path in source_dir.rglob("*.py")
		if not any(
			part in _SKIP_DIRECTORY_NAMES or part.startswith(".")
			for part in path.relative_to(source_dir).parts[:-1]
		)
	)


def _docstring(node: ast.AST) -> str:
	value = ast.get_docstring(node, clean=True)
	return textwrap.dedent(value).strip() if value else "_No docstring provided._"


def _signature(node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> str:
	prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
	parameters = ast.unparse(node.args)
	returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
	return f"{prefix}def {node.name}({parameters}){returns}"


def _render_function(
	node: Union[ast.FunctionDef, ast.AsyncFunctionDef], heading_level: int, label: str
) -> list[str]:
	heading = "#" * heading_level
	return [
		f"{heading} {label}: `{_signature(node)}`",
		"",
		_docstring(node),
		"",
	]


def _render_class(node: ast.ClassDef) -> list[str]:
	lines = [f"### Class: `{node.name}`", "", _docstring(node), ""]
	methods = [
		child
		for child in node.body
		if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
		and not child.name.startswith("_")
	]
	for method in methods:
		lines.extend(_render_function(method, 4, "Method"))
	return lines


def _render_module(path: Path, source_dir: Path) -> str:
	source = path.read_text(encoding="utf-8")
	module = ast.parse(source, filename=str(path))
	relative_path = path.relative_to(source_dir).as_posix()
	lines = [
		f"## Module: `{relative_path}`",
		"",
		_docstring(module),
		"",
	]

	public_definitions = [
		node
		for node in module.body
		if isinstance(node, ast.ClassDef)
		or isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
		if not node.name.startswith("_")
	]
	if not public_definitions:
		lines.extend(["_No public top-level classes or functions._", ""])
		return "\n".join(lines)

	for node in public_definitions:
		if isinstance(node, ast.ClassDef):
			lines.extend(_render_class(node))
		else:
			lines.extend(_render_function(node, 3, "Function"))
	return "\n".join(lines)


def generate_markdown(
	source_dir: PathLike, output_file: Optional[PathLike] = None
) -> str:
	"""Scan Python files and optionally write generated Markdown to a file.

	Source code is parsed with ``ast`` and is never imported or executed. Hidden
	directories and common virtual-environment/build directories are excluded.
	"""
	root = Path(source_dir)
	if not root.is_dir():
		raise NotADirectoryError(f"Source directory does not exist: {root}")

	files = _python_files(root)
	lines = [
		"# Generated Source Documentation",
		"",
		f"Source directory: `{root.name or root.as_posix()}`",
		"",
	]
	if files:
		for path in files:
			lines.append(_render_module(path, root).rstrip())
			lines.append("")
	else:
		lines.extend(["_No Python source files were found._", ""])

	markdown = "\n".join(lines).rstrip() + "\n"
	if output_file is not None:
		destination = Path(output_file)
		destination.parent.mkdir(parents=True, exist_ok=True)
		destination.write_text(markdown, encoding="utf-8")
	return markdown


def main() -> int:
	parser = argparse.ArgumentParser(
		description="Generate Markdown reference documentation from Python files."
	)
	parser.add_argument("source_dir", type=Path, help="Directory containing Python source")
	parser.add_argument("output_file", type=Path, help="Path for generated Markdown")
	arguments = parser.parse_args()

	try:
		generate_markdown(arguments.source_dir, arguments.output_file)
	except (OSError, SyntaxError) as error:
		print(f"Documentation generation failed: {error}", file=sys.stderr)
		return 1
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
