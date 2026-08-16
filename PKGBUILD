# Maintainer: Feedback Hub for Linux Maintainers <maintainer@example.local>
# 架构：Arch Linux (AUR)
# 构建：在仓库根目录执行 `makepkg`（源码文件直接来自仓库根目录）。
# 注意：source 必须为空。makepkg 对带子目录的本地文件 source 只按 basename
# 在顶层查找，feedbackhub/ 下的文件会找不到；改为在 package() 里用 $startdir
# 直接从仓库根目录复制。

pkgname=feedbackhub
pkgver=1.0.0
pkgrel=1
pkgdesc="Linux 反馈中心的本地应用（所有数据仅保存在本机，不联网）"
arch=('any')
url="https://example.local/feedbackhub"
license=('GPL3')
depends=('python' 'python-gobject' 'gtk3')
makedepends=()
source=()
sha256sums=()

package() {
  # 启动脚本
  install -Dm755 "$startdir/bin/feedbackhub" "$pkgdir/usr/bin/feedbackhub"

  # Python 包
  install -d "$pkgdir/usr/lib/feedbackhub"
  cp -r "$startdir/feedbackhub" "$pkgdir/usr/lib/feedbackhub/"

  # 桌面文件
  install -Dm644 "$startdir/feedbackhub.desktop" \
    "$pkgdir/usr/share/applications/feedbackhub.desktop"

  # 图标
  install -Dm644 "$startdir/feedbackhub/assets/icon.svg" \
    "$pkgdir/usr/share/icons/hicolor/scalable/apps/feedbackhub.svg"
}