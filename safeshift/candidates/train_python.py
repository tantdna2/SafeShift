"""Single source/hash/size-locked software runtime; never fetches model weights."""
import os
from pathlib import Path, PurePosixPath
import platform
import posixpath
import shutil
import tarfile
import time
from urllib.parse import urlparse
from urllib.request import urlopen

from safeshift.pilot.artifacts import read, relative, sha, write
from .source import require


def extract(archive, target, lock):
    """Validate the entire bounded table, then files, then internal symlinks.

    No extractall, hardlinks, devices, sparse files, link ancestors, absolute
    paths, duplicate names, or privilege bits. Links may only target an admitted
    regular file inside python/, and are installed last in a fresh private tree.
    """
    require(not any(p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction())
                    for p in (target, *target.parents)), "PYTHON_EXTRACTION_TARGET_ALIAS")
    require(archive.stat().st_size == lock["size_bytes"] and sha(archive) == lock["sha256"],
            "PYTHON_ARCHIVE_SIZE_OR_SHA256")
    target.mkdir(mode=0o700, exist_ok=False)
    with tarfile.open(archive, "r:gz") as bundle:
        entries, total = {}, 0
        for member in bundle:
            require(len(entries) < lock["max_members"], "PYTHON_ARCHIVE_MEMBER_BOUND")
            name = member.name.rstrip("/")
            relative(name)
            require(name == "python" or name.startswith("python/"), "PYTHON_ARCHIVE_ROOT")
            require(name not in entries, "PYTHON_ARCHIVE_DUPLICATE")
            require((member.isdir() or member.isreg() or member.issym()) and not member.sparse,
                    "PYTHON_ARCHIVE_ENTRY_TYPE")
            require(not member.mode & 0o7000, "PYTHON_ARCHIVE_PRIVILEGE_BITS")
            total += member.size
            require(0 <= member.size and total <= lock["max_uncompressed_bytes"], "PYTHON_ARCHIVE_SIZE_BOUND")
            entries[name] = member
        for name, member in entries.items():
            for parent in PurePosixPath(name).parents:
                if str(parent) != "." and str(parent) in entries:
                    require(entries[str(parent)].isdir(), "PYTHON_ARCHIVE_LINK_ANCESTOR")
            if member.issym():
                link = member.linkname
                require(link and not link.startswith("/") and "\\" not in link and ":" not in link,
                        "PYTHON_ARCHIVE_LINK_ESCAPE")
                resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), link))
                require(resolved.startswith("python/") and resolved in entries and entries[resolved].isreg(),
                        "PYTHON_ARCHIVE_LINK_TARGET")
        for name, member in entries.items():
            if member.issym():
                continue
            path = target / name
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                with bundle.extractfile(member) as source, path.open("xb") as out:
                    shutil.copyfileobj(source, out, 2**20)
                path.chmod(0o755 if member.mode & 0o111 else 0o644)
        for name, member in entries.items():
            if member.issym():
                path = target / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.symlink_to(member.linkname)
    python = target / "python/bin/python3.11"
    require(python.is_file() and not python.is_symlink(), "PYTHON_EXECUTABLE_REQUIRED")
    return python, {"members": len(entries), "uncompressed_bytes": total, "safe_extraction": "PASS"}


def provision(repo, scratch, output, env, deadline):
    from safeshift.pilot import bootstrap as boot
    lock = read(Path(repo) / "configs/candidate160/python3119.json")
    require(platform.system() == "Linux" and platform.machine() == "x86_64", "PYTHON_PROVIDER_LINUX_X86_64_ONLY")
    require(lock["version"] == "3.11.9" and lock["target"] == "x86_64-unknown-linux-gnu",
            "PYTHON_PROVIDER_TARGET")
    archive = Path(scratch) / "python3119.tar.gz"
    receipt = {"status": "BLOCKED", "lock": lock, "final_url": None}
    try:
        remaining = deadline - time.monotonic()
        require(remaining > 0, "TIME_CAP_PYTHON_DOWNLOAD")
        with urlopen(lock["url"], timeout=min(60, remaining)) as response, archive.open("xb") as out:
            parsed = urlparse(response.geturl())
            require(parsed.scheme == "https" and parsed.hostname in
                    ("github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"),
                    "PYTHON_DOWNLOAD_REDIRECT")
            receipt["final_url"] = parsed.scheme + "://" + parsed.netloc + parsed.path  # omit signed query
            size = 0
            while True:
                require(time.monotonic() < deadline, "TIME_CAP_PYTHON_DOWNLOAD")
                block = response.read(2**20)
                if not block:
                    break
                size += len(block)
                require(size <= lock["size_bytes"], "PYTHON_DOWNLOAD_SIZE_BOUND")
                out.write(block)
            out.flush()
            os.fsync(out.fileno())
        receipt.update(downloaded_bytes=size, observed_sha256=sha(archive))
        python, extraction = extract(archive, Path(scratch) / "cpython3119", lock)
        receipt["extraction"] = extraction
        receipt["probe"] = boot.probe_interpreter(python, env)
        require(receipt["probe"].get("eligible") and receipt["probe"].get("version") == [3, 11, 9],
                "DOWNLOADED_PYTHON_PROBE_FAILED")
        receipt["status"] = "PASS"
        return python
    except BaseException as error:
        receipt["error"] = {"type": type(error).__name__, "message": str(error)[:1000]}
        raise
    finally:
        write(Path(output) / "python_provider.json", receipt)
