"""Deployable loopback authority; hosting/TLS/storage approval is separate."""
import argparse
from http.server import HTTPServer
from pathlib import Path
from safeshift.internvl3763_witness import Store, handler
from safeshift.kaggle_handoff import private_root, lock
from safeshift.pilot.artifacts import safe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8763)
    args = parser.parse_args()
    root = private_root(args.directory)
    root.mkdir(parents=True, exist_ok=True)
    # Process death releases the socket/OS lock, never the permanent claims.
    with lock(root, "witness.lock"):
        store = Store(safe(root, "claims.sqlite3"))
        print("Witness database identity: " + store.identity, flush=True)
        HTTPServer(("127.0.0.1", args.port), handler(store)).serve_forever()


if __name__ == "__main__":
    main()
