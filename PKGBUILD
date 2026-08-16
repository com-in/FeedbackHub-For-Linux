# Maintainer: Feedback Hub for Linux Maintainers <maintainer@example.local>
# 架构：Arch Linux (AUR)
# 构建：在本目录执行 `makepkg`（需已 clone 本仓库，文件源码位于同目录）。

pkgname=feedbackhub
pkgver=1.0.0
pkgrel=1
pkgdesc="Linux 反馈中心的本地应用（所有数据仅保存在本机，不联网）"
arch=('any')
url="https://example.local/feedbackhub"
license=('MIT')
depends=('python' 'python-gobject' 'gtk3')
makedepends=()
source=(
  "feedbackhub/__init__.py"
  "feedbackhub/__main__.py"
  "feedbackhub/app.py"
  "feedbackhub/views.py"
  "feedbackhub/data.py"
  "feedbackhub/styles.css"
  "feedbackhub/assets/icon.svg"
  "bin/feedbackhub"
  "feedbackhub.desktop"
)
sha256sums=('SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP')

package() {
  # 启动脚本
  install -Dm755 "$srcdir/bin/feedbackhub" "$pkgdir/usr/bin/feedbackhub"

  # Python 包
  install -d "$pkgdir/usr/lib/feedbackhub"
  cp -r "$srcdir/feedbackhub" "$pkgdir/usr/lib/feedbackhub/"

  # 桌面文件
  install -Dm644 "$srcdir/feedbackhub.desktop" \
    "$pkgdir/usr/share/applications/feedbackhub.desktop"

  # 图标
  install -Dm644 "$srcdir/feedbackhub/assets/icon.svg" \
    "$pkgdir/usr/share/icons/hicolor/scalable/apps/feedbackhub.svg"
}