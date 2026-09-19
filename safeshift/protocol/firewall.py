"""Fail closed on benchmark paths before opening any development input."""

from pathlib import Path, PureWindowsPath


class BenchmarkFirewallError(ValueError):
    pass


def external_path(repo: Path, value: str | Path) -> Path:
    """Require repository-relative paths; reject raw data, aliases and traversal.

    This is a path firewall, not a content/provenance detector for copied images.
    Repository root is supplied by the application, never by an input manifest.
    """
    text = str(value).replace("\\", "/")
    parts = text.casefold().split("/")
    if any(part.startswith("inspecsafe") for part in parts):
        raise BenchmarkFirewallError("BENCHMARK FIREWALL: InspecSafe input forbidden")
    if any(parts[i:i + 2] == ["data", "raw"] for i in range(len(parts))):
        raise BenchmarkFirewallError("BENCHMARK FIREWALL: raw dataset input forbidden")
    if (not text or Path(text).is_absolute() or PureWindowsPath(text).drive
            or ".." in parts or ":" in text):
        raise BenchmarkFirewallError("BENCHMARK FIREWALL: use a repository-relative path without traversal")
    root = repo.resolve()
    resolved = (root / text).resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise BenchmarkFirewallError("BENCHMARK FIREWALL: path escapes repository") from exc
    resolved_parts = [part.casefold() for part in relative.parts]
    if (any(part.startswith("inspecsafe") for part in resolved_parts)
            or resolved_parts[:2] == ["data", "raw"]):
        raise BenchmarkFirewallError("BENCHMARK FIREWALL: alias resolves to raw benchmark data")
    return resolved
