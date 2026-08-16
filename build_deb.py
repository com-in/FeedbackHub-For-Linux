#!/usr/bin/env python3
"""构建 Debian 安装包（.deb）。

纯 Python 实现，可在任意平台（含 Windows）生成 .deb：
  - 将 feedbackhub 包、启动脚本、桌面文件、图标打包进 data.tar.gz
  - 生成 control.tar.gz
  - 用 ar 归档格式组装 debian-binary + control + data

用法：python build_deb.py [--out DIST_DIR]
"""
import io
import os
import shutil
import sys
import tarfile
import time

import feedbackhub

ROOT = os.path.dirname(os.path.abspath(__file__))
PKG = "feedbackhub"
VERSION = feedbackhub.__version__
ARCH = "all"
MAINTAINER = "Feedback Hub Maintainers <maintainer@example.local>"
DESC = ("A local app for the Linux Feedback Hub. "
        "All feedback data is stored locally; nothing is uploaded.")

DEPS = ", ".join([
    "python3",
    "python3-gi",
    "gir1.2-gtk-3.0",
])


def _install(root_dir):
    """把文件按目标布局写入 root_dir（使用 usr/... 相对路径）。"""
    usr = os.path.join(root_dir, "usr")

    # 启动脚本 -> /usr/bin/feedbackhub
    # 必须以二进制模式写入并显式用 \n，避免 Windows 下写入 CRLF 污染 shebang，
    # 否则 Linux 启动时会报 "env: 'python3\r': No such file or directory"。
    bin_dir = os.path.join(usr, "bin")
    os.makedirs(bin_dir, exist_ok=True)
    launcher = os.path.join(bin_dir, "feedbackhub")
    with open(launcher, "wb") as f:
        f.write(
            b"#!/usr/bin/env python3\n"
            b"import sys\n"
            b"sys.path.insert(0, '/usr/lib/feedbackhub')\n"
            b"from feedbackhub.app import run\n"
            b"sys.exit(run())\n")
    os.chmod(launcher, 0o755)

    # Python 包 -> /usr/lib/feedbackhub/feedbackhub/（标准 Debian 布局）
    lib_dir = os.path.join(usr, "lib", PKG, PKG)  # usr/lib/feedbackhub/feedbackhub
    os.makedirs(lib_dir, exist_ok=True)
    srcpkg = os.path.join(ROOT, "feedbackhub")
    for name in os.listdir(srcpkg):
        src = os.path.join(srcpkg, name)
        if name == "__pycache__" or name.startswith("."):
            continue
        dst = os.path.join(lib_dir, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(src, dst)

    # 桌面文件 -> /usr/share/applications/
    app_dir = os.path.join(usr, "share", "applications")
    os.makedirs(app_dir, exist_ok=True)
    shutil.copy2(os.path.join(ROOT, "feedbackhub.desktop"), app_dir)

    # 图标 -> /usr/share/icons/...
    icon_dir = os.path.join(usr, "share", "icons", "hicolor", "scalable", "apps")
    os.makedirs(icon_dir, exist_ok=True)
    shutil.copy2(os.path.join(srcpkg, "assets", "icon.svg"),
                 os.path.join(icon_dir, "feedbackhub.svg"))

    # 文档
    doc_dir = os.path.join(usr, "share", "doc", PKG)
    os.makedirs(doc_dir, exist_ok=True)
    with open(os.path.join(doc_dir, "copyright"), "w", encoding="utf-8") as f:
        f.write("Copyright (c) 2026 Feedback Hub for Linux\n"
                "License: GPL-3.0-or-later\n")
    if os.path.exists(os.path.join(ROOT, "README.md")):
        shutil.copy2(os.path.join(ROOT, "README.md"),
                     os.path.join(doc_dir, "README"))


def _make_tar_bytes(entries):
    """entries: list of (物理路径或None, tar内路径)。

    若物理路径为空字符串，则该条目为根目录 "."；
    若物理路径为 None，则该条目为目录（无内容）；
    否则为普通文件。
    """
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", format=tarfile.USTAR_FORMAT) as tar:
        for fpath, arcname in entries:
            ti = tarfile.TarInfo(name=arcname)
            ti.mtime = 0
            ti.uname = "root"
            ti.gname = "root"
            if fpath == "dir":
                ti.type = tarfile.DIRTYPE
                ti.mode = 0o755
                ti.size = 0
                tar.addfile(ti)
            else:
                if fpath.endswith(("feedbackhub", "feedbackhub.sh")):
                    ti.mode = 0o755
                else:
                    ti.mode = 0o644
                ti.size = os.path.getsize(fpath)
                ti.type = tarfile.REGTYPE
                with open(fpath, "rb") as f:
                    tar.addfile(ti, f)
    return buf.getvalue()


# 向后兼容（之前仅支持文件的调用）
def _make_tar_bytes_with_dirs(entries):
    return _make_tar_bytes(entries)


def _control_bytes(installed_size_kb):
    # Description 第二行起需以空格开头
    long_desc = (
        " A local desktop app for the Linux Feedback Hub.\n"
        " All feedback data is stored locally under "
        "~/.local/share/feedbackhub/; nothing is uploaded.\n"
        " Built with Python 3 and GTK 3."
    )
    ctrl = (
        "Package: %s\n"
        "Version: %s\n"
        "Architecture: %s\n"
        "Maintainer: %s\n"
        "Depends: %s\n"
        "Section: utils\n"
        "Priority: optional\n"
        "Installed-Size: %d\n"
        "Description: %s\n"
        "%s\n"   # 末尾补换行符（deb822 规范要求）
    ) % (PKG, VERSION, ARCH, MAINTAINER, DEPS, installed_size_kb, DESC, long_desc)
    return ctrl.encode("utf-8")


def _ar_archive(members):
    """members: list of (name, data bytes)。返回 ar 归档字节。

    严格遵循 ar/deb 规范：name 左对齐，数字字段右对齐（左补空格）。
    mtime/uid/gid/mode/size 均用标准占位。mtime=0 提升可重复性。
    """
    out = io.BytesIO()
    out.write(b"!<arch>\n")
    for name, data in members:
        # 长度分别：name=16, mtime=12, uid=6, gid=6, mode=8, size=10, 末尾 `\n
        header = "%-16s%12d%6d%6d%8o%10d`\n" % (
            name[:16], 0, 0, 0, 0o100644, len(data))
        out.write(header.encode("ascii"))
        out.write(data)
        if len(data) % 2:
            out.write(b"\n")
    return out.getvalue()


def build(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    staging = os.path.join(out_dir, "_stage")
    if os.path.exists(staging):
        shutil.rmtree(staging)
    _install(staging)

    # 计算 Installed-Size（KB，向上取整）
    total_bytes = 0
    data_entries = []
    for base, _, files in os.walk(staging):
        for fname in files:
            fpath = os.path.join(base, fname)
            total_bytes += os.path.getsize(fpath)
            rel = os.path.relpath(fpath, staging).replace("\\", "/")
            data_entries.append((fpath, "./" + rel))
    installed_size_kb = (total_bytes + 1023) // 1024

    # 收集所有需要出现在 data.tar.gz 中的目录条目（dpkg 解包时需先有父目录）。
    # 目录条目以 "usr/" 开头（不带 ./ 前缀，与 dpkg-deb 输出保持一致）。
    data_dirs = set()
    for fpath, arc in data_entries:
        d = os.path.dirname(arc)  # 比如 "./usr/lib/feedbackhub"
        d = d[2:] if d.startswith("./") else d  # 去 ./，变成 "usr/lib/feedbackhub"
        while d:
            data_dirs.add(d)
            d = os.path.dirname(d)
    sorted_dirs = sorted(data_dirs, key=lambda x: x.count("/"))

    data_tar = _make_tar_bytes(
        [("dir", d) for d in sorted_dirs] + data_entries
    )

    # control.tar.gz：存放 ./control 与 ./md5sums（标准 dpkg-deb 布局，无 DEBIAN/ 前缀）
    ctrl_dir = staging + "_debian"
    if os.path.exists(ctrl_dir):
        shutil.rmtree(ctrl_dir)
    os.makedirs(ctrl_dir)
    control_path = os.path.join(ctrl_dir, "control")
    with open(control_path, "wb") as f:
        f.write(_control_bytes(installed_size_kb))
    # 计算 md5sums（排序保证可重复性）
    md5_lines = []
    entries = []
    for fpath, arc in data_entries:
        import hashlib
        with open(fpath, "rb") as f:
            h = hashlib.md5(f.read()).hexdigest()
        entries.append((arc, h))
    entries.sort()
    for arc, h in entries:
        md5_lines.append("%s  %s\n" % (h, arc))
    md5_path = os.path.join(ctrl_dir, "md5sums")
    with open(md5_path, "w", encoding="utf-8") as f:
        f.writelines(md5_lines)
    control_tar = _make_tar_bytes([
        (control_path, "./control"),
        (md5_path, "./md5sums"),
    ])

    deb = _ar_archive([
        ("debian-binary", b"2.0\n"),
        ("control.tar.gz", control_tar),
        ("data.tar.gz", data_tar),
    ])

    deb_path = os.path.join(out_dir, "%s_%s_%s.deb" % (PKG, VERSION, ARCH))
    with open(deb_path, "wb") as f:
        f.write(deb)

    shutil.rmtree(staging)
    shutil.rmtree(ctrl_dir)
    print("OK: %s (%d bytes)" % (deb_path, len(deb)))
    return deb_path


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "dist")
    build(out)