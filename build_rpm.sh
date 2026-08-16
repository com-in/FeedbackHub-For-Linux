#!/usr/bin/env bash
# 在 Fedora/RHEL 上用 rpmbuild 生成 .rpm 安装包。
# 用法：bash build_rpm.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

VERSION="$(python3 -c 'import feedbackhub; print(feedbackhub.__version__)')"
PKG="feedbackhub"
SPEC="$ROOT/${PKG}.spec"
OUTDIR="$ROOT/dist"

# 准备 rpmbuild 工作目录
: "${RPM_TOP:=$HOME/rpmbuild}"
mkdir -p "$RPM_TOP"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# 生成源码 tar 包（feedbackhub-<version>.tar.gz），spec 的 Source0 需要它
# build_tar.py 输出顶层目录为 feedbackhub-<version>，与 %setup -n 匹配
python3 build_tar.py "$RPM_TOP/SOURCES" >/dev/null
TARBALL="$RPM_TOP/SOURCES/feedbackhub-${VERSION}.tar.gz"

# spec 引用 ${PKG}-${VERSION} 目录，需保证内部顶层目录名一致
if [ ! -f "$TARBALL" ]; then
  echo "错误：未生成源码包 $TARBALL" >&2
  exit 1
fi

# 构建
mkdir -p "$OUTDIR"
rpmbuild -bb --define "_topdir $RPM_TOP" "$SPEC"

# 收集产物
cp "$RPM_TOP"/RPMS/noarch/${PKG}-${VERSION}-*.rpm "$OUTDIR/"
echo "OK: $(ls "$OUTDIR"/${PKG}-${VERSION}-*.rpm)"