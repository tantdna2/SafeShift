"""Exact public snapshot admission, shared with the PR150 CPU probe."""
import shutil
import stat
from pathlib import Path
from safeshift.pilot.artifacts import read, sha

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "configs/cpu_g2_g3/public_source_lock.json"

def require(value, message):
    if not value:
        raise ValueError(message)

def snapshot_stat(path, *, directory=False):
    """Inspect the entry itself, including Windows junction/reparse attributes."""
    path = Path(path)  # Accept CLI/os.PathLike values without resolving aliases.
    info = path.lstat()
    require(not stat.S_ISLNK(info.st_mode) and
            not (getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT),
            "SOURCE_ALIAS_FORBIDDEN")
    require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode),
            "SNAPSHOT_DIRECTORY_REQUIRED" if directory else "SOURCE_REGULAR_FILE_REQUIRED")
    if not directory:
        require(info.st_nlink == 1, "SOURCE_ALIAS_FORBIDDEN")
    return info


def verify_snapshot(snapshot, key, lock=LOCK):
    """Never execute local Python until every public source byte is locked."""
    snapshot = Path(snapshot)
    spec = read(lock)[key]
    snapshot_stat(snapshot, directory=True)
    # Enumerate ALL entries, including hidden names and dangling/directory links.
    # Do not recurse into any directory or follow an entry to classify it.
    actual = {p.name for p in snapshot.iterdir()}
    require(actual == set(spec["files"]), "SNAPSHOT_EXACT_ALLOWLIST_REQUIRED")
    for name, checksum in spec["files"].items():
        p = snapshot / name
        snapshot_stat(p)
        require(sha(p) == checksum, "SOURCE_CHECKSUM:" + name)
    return spec


def stage_snapshot(snapshot, local, key, lock=LOCK):
    """Copy only locked flat files; revalidate both trees before any remote import."""
    snapshot, local = Path(snapshot), Path(local)
    spec = verify_snapshot(snapshot, key, lock)
    local.mkdir(exist_ok=False)
    for name in spec["files"]:
        snapshot_stat(snapshot / name)
        # A link introduced after validation must not be followed by the copy.
        # The destination check below also rejects links and changed file bytes.
        shutil.copyfile(snapshot / name, local / name, follow_symlinks=False)
    require(verify_snapshot(snapshot, key, lock) == spec, "SOURCE_LOCK_CHANGED_DURING_COPY")
    require(verify_snapshot(local, key, lock) == spec, "SOURCE_LOCK_CHANGED_DURING_COPY")
    return spec


def verify_module_cache(cache, spec):
    """Inspect the dedicated HF Python cache BEFORE any remote module executes.

    Reject bytecode and nonempty package initializers as well as changed source.
    This is admission against a stale/poisoned cache, not an OS remote-code sandbox.
    """
    cache = Path(cache)
    expected = {name: digest for name, digest in spec["files"].items() if name.endswith(".py")}
    for directory, allowed in ((cache, {"__init__.py", "transformers_modules"}),
                               (cache/"transformers_modules", {"__init__.py", spec["revision"]}),
                               (cache/"transformers_modules"/spec["revision"], {"__init__.py", *expected})):
        if not directory.exists() and not directory.is_symlink():
            continue
        snapshot_stat(directory, directory=True)
        for path in directory.iterdir():
            require(path.name in allowed, "REMOTE_CACHE_EXTRA_ENTRY:" + path.name)
            if path.name in ("transformers_modules", spec["revision"]):
                snapshot_stat(path, directory=True)
            else:
                snapshot_stat(path)
                if path.name == "__init__.py":
                    require(path.read_bytes() == b"", "REMOTE_CACHE_PACKAGE_CODE")
                else:
                    require(sha(path) == expected[path.name], "REMOTE_CACHE_SOURCE_HASH:" + path.name)
