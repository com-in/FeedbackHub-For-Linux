# 反馈中心（Feedback Hub for Linux）

一款**完全本地运行**、Linux 反馈中心（Feedback Hub）的桌面应用。

- 界面与交互参照原版，浅色 Fluent 风格
- **所有数据仅保存在本机，不发送任何数据**
- 反馈、投票、评论等数据仅保存在本机 `~/.local/share/feedbackhub/`

## 功能

- 首页：报告问题 / 建议新功能入口、分类快捷入口、最近反馈
- 反馈列表：按产品筛选、按最新/最多投票排序、关键词搜索
- 新建反馈向导：多步流程（类型 → 详情 → 查找类似反馈 → 类别 → 提交）
- 反馈详情：状态徽章、投票、评论、添加评论
- 我的反馈：查看自己提交的反馈及状态
- 设置：数据存储位置、主题、版本信息

## 快捷键（参照原版）

| 快捷键 | 功能 |
| --- | --- |
| `Ctrl + F` | 聚焦搜索框（搜索反馈） |
| `Ctrl + N` | 新建反馈 |
| `Ctrl + 1 / 2 / 3 / 4` | 首页 / 反馈 / 我的反馈 / 设置 |
| `Ctrl + Enter` | 提交反馈 |
| `Ctrl + V` | 在新建反馈中粘贴截图 |
| `A` | 在详情页为当前反馈投票 |
| `Esc` | 从详情返回反馈列表 |

> 原版使用 `Win + F` 打开反馈中心。在 Linux 下，请在桌面环境（如 GNOME/KDE）的
> 自定义快捷键中绑定 `feedbackhub` 命令即可还原这一习惯。

## 运行

```bash
# 直接运行（源码方式）
python3 -m feedbackhub
# 或
./bin/feedbackhub
```

依赖：`python3`、`python3-gi`（PyGObject）、`gtk3`（GObject Introspection）。

## 安装包

### Debian / Ubuntu 等（.deb）

在项目目录执行：

```bash
python3 build_deb.py
```

生成 `dist/feedbackhub_1.0.0_all.deb`，然后：

```bash
sudo dpkg -i dist/feedbackhub_1.0.0_all.deb
sudo apt-get install -f   # 自动补齐依赖
```

### Arch Linux（AUR / PKGBUILD）

已附 `PKGBUILD`，在有 Arch 工具链的系统上执行：

```bash
makepkg -si
```

也可将本仓库发布为 AUR 软件包，用户通过 aur 助手安装。

### 通用（tar.gz 源码包）

```bash
python3 build_tar.py
```

生成 `dist/feedbackhub-1.0.0.tar.gz`，解压后在任意发行版按“运行”一节使用。

## 项目结构

```
feedbackhub/          # Python 包
  app.py              # 主窗口、导航、快捷键
  views.py            # 各页面视图与新建反馈向导
  data.py             # 本地 JSON 数据层
  styles.css          # GTK 样式
  assets/icon.svg     # 应用图标
bin/feedbackhub       # 启动脚本
build_deb.py          # 构建 .deb
build_tar.py          # 构建通用 tar 包
PKGBUILD              # Arch Linux 打包
feedbackhub.desktop   # 桌面入口
```

## 许可

MIT License