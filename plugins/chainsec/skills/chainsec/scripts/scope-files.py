#!/usr/bin/env python3
"""Print preflight scope as JSON: scope_files count and ROOT-relative files."""
import argparse
import json
import os

from _common import load_json, scope_files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--pack", required=True)
    args = parser.parse_args()
    if not os.path.isdir(args.root):
        parser.error("--root must be an existing directory")
    files = scope_files(args.root, load_json(args.pack)["scope"])
    print(json.dumps({"scope_files": len(files), "files": files}))


if __name__ == "__main__":
    main()
