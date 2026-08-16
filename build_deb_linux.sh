#!/usr/bin/env bash
# 在 Linux 上用系统自带 dpkg-deb 生成 100% 标准的 .deb 安装包。
# 用法：bash build_deb_linux.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PKG="feedbackhub"
VERSION="$(cd "$ROOT" && python3 -c 'import feedbackhub; print(feedbackhub.__version__)')"
ARCH="all"
OUT="$ROOT/dist/${PKG}_${VERSION}_${ARCH}.deb"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

load_pkg() {
  # 生成文件树
  mkdir -p "$STAGE/usr/bin"
  mkdir -p "$STAGE/usr/lib/$PKG"
  mkdir -p "$STAGE/usr/share/applications"
  mkdir -p "$STAGE/usr/share/icons/hicolor/scalable/apps"
  mkdir -p "$STAGE/usr/share/doc/$PKG"
  mkdir -p "$STAGE/DEBIAN"

  # 启动脚本
  cat > "$STAGE/usr/bin/feedbackhub" <<'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/usr/lib/feedbackhub')
from feedbackhub.app import run
sys.exit(run())
EOF
  chmod 755 "$STAGE/usr/bin/feedbackhub"

  # Python 包
  cp -r "$ROOT/feedbackhub/." "$STAGE/usr/lib/$PKG/"
  find "$STAGE/usr/lib/$PKG" -name '__pycache__' -type d -prune -exec rm -rf {} +
  find "$STAGE/usr/lib/$PKG" -name '*.pyc' -delete

  # 桌面文件与图标
  cp "$ROOT/feedbackhub.desktop" "$STAGE/usr/share/applications/"
  cp "$ROOT/feedbackhub/assets/icon.svg" \
     "$STAGE/usr/share/icons/hicolor/scalable/apps/$PKG.svg"

  # 文档
  cp "$ROOT/README.md" "$STAGE/usr/share/doc/$PKG/README"
  cat > "$STAGE/usr/share/doc/$PKG/copyright" <<'EOF'
Copyright (c) 2026 Feedback Hub for Linux
License: MIT
EOF

  # control 文件（由 dpkg-deb 自动生成 md5sums）
  cat > "$STAGE/DEBIAN/control" <<EOF
Package: $PKG
Version: $VERSION
Architecture: $ARCH
Maintainer: Feedback Hub Maintainers <maintainer@example.local>
Depends: python3, python3-gi, gir1.2-gtk-3.0
Section: utils
Priority: optional
Description: A local app for the Linux Feedback Hub.
 All feedback data is stored locally; nothing is uploaded.
 Built with Python 3 and GTK 3.
EOF
}

build() {
  load_pkg
  mkdir -p "$(dirname "$OUT")"
  dpkg-deb --build "$STAGE" "$OUT"
  echo "OK: $OUT"
}

build "$@"