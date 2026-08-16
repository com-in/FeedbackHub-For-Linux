#!/usr/bin/env python3
"""构建通用 tar.gz 源码包，可在任意 Linux 发行版解压后直接运行。"""
import os
import shutil
import sys
import tarfile

import feedbackhub

ROOT = os.path.dirname(os.path.abspath(__file__))
VERSION = feedbackhub.__version__
NAME = "feedbackhub-%s" % VERSION

INCLUDE = [
    "feedbackhub",
    "bin",
    "feedbackhub.desktop",
    "README.md",
]


def build(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    staging = os.path.join(out_dir, NAME)
    if os.path.exists(staging):
        shutil.rmtree(staging)
    os.makedirs(staging)
    for item in INCLUDE:
        src = os.path.join(ROOT, item)
        dst = os.path.join(staging, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(src, dst)

    path = os.path.join(out_dir, NAME + ".tar.gz")
    with tarfile.open(path, "w:gz") as tar:
        tar.add(staging, arcname=NAME)
    shutil.rmtree(staging)
    print("OK: %s" % path)
    return path


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "dist")
    build(out)