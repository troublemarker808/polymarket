import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_ROOT = ROOT / "src" / "pm_bot" / "strategies"
CATEGORY_NAMES = {"sports", "crypto", "weather"}


def test_strategy_packages_do_not_cross_import_categories_or_adapters() -> None:
    violations: list[str] = []

    for path in STRATEGY_ROOT.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        category = _category_for_strategy_file(path)
        module_parts = _module_parts_for_file(path)

        for node in ast.walk(tree):
            imported_modules = _imported_modules(node=node, module_parts=module_parts)
            for imported in imported_modules:
                if imported.startswith("pm_bot.adapters.polymarket"):
                    violations.append(
                        f"{path.relative_to(ROOT)}:{getattr(node, 'lineno', '?')} imports adapter boundary {imported}"
                    )
                if category is None:
                    continue
                for sibling in CATEGORY_NAMES - {category}:
                    if imported.startswith(f"pm_bot.strategies.{sibling}"):
                        violations.append(
                            f"{path.relative_to(ROOT)}:{getattr(node, 'lineno', '?')} crosses strategy boundary via {imported}"
                        )

    assert violations == []


def _category_for_strategy_file(path: Path) -> str | None:
    relative = path.relative_to(STRATEGY_ROOT)
    if len(relative.parts) < 2:
        return None
    category = relative.parts[0]
    return category if category in CATEGORY_NAMES else None


def _module_parts_for_file(path: Path) -> list[str]:
    relative = path.relative_to(ROOT / "src")
    if path.name == "__init__.py":
        return list(relative.with_suffix("").parts[:-1])
    return list(relative.with_suffix("").parts)


def _imported_modules(node: ast.AST, module_parts: list[str]) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        return [_resolve_from_import(node=node, module_parts=module_parts)]
    return []


def _resolve_from_import(node: ast.ImportFrom, module_parts: list[str]) -> str:
    module = node.module or ""
    if node.level == 0:
        return module

    package_parts = module_parts[:-1]
    if node.level > 1:
        package_parts = package_parts[: -(node.level - 1)]
    resolved = package_parts + ([module] if module else [])
    return ".".join(part for part in resolved if part)
