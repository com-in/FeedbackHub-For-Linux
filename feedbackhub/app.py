"""应用主窗口：导航、全局快捷键与应用内快捷键、主题与 CSS 加载。"""
import os
import sys

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GObject, GLib  # noqa: E402

from . import __version__, APP_NAME
from .data import DataStore, Prefs

_HERE = os.path.dirname(os.path.abspath(__file__))
CSS_PATH = os.path.join(_HERE, "styles.css")


def load_css():
    """加载主题 CSS。

    绝不抛出异常：GTK 的 CSS 解析器在出问题时（屏幕为 None、属性不支持等）
    只会打印警告。但一旦在此抛异常，PyGObject 会把它吞进信号回调，
    导致 activate 中断、窗口永远不显示——这正是"没报错却弹不出窗口"的根因。
    因此这里必须兜底：任何失败都只打印到 stderr，不阻断窗口创建。
    """
    try:
        provider = Gtk.CssProvider()
        provider.load_from_path(CSS_PATH)
        screen = Gdk.Screen.get_default()
        if screen is not None:
            Gtk.StyleContext.add_provider_for_screen(
                screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        else:
            sys.stderr.write("[feedbackhub] 警告: 未获取到默认屏幕，跳过 CSS 加载\n")
    except Exception as e:  # noqa: BLE001
        sys.stderr.write("[feedbackhub] 警告: CSS 加载失败，已忽略: %r\n" % (e,))


class AppWindow(Gtk.Window):
    """主窗口。持有导航状态、数据存储，并暴露出视图所需的上下文方法。

    刻意使用最基础的 Gtk.Window + Gtk.main()，而不是 Gtk.Application：
    Gtk.Application 依赖 D-Bus session bus 注册 application_id，在
    VMware / 无桌面会话 / 未设 DBUS_SESSION_BUS_ADDRESS 的环境下，
    activate 信号永远不会触发，导致进程直接退出、无窗口、无报错。
    """

    def __init__(self):
        super().__init__(title=APP_NAME)
        self.store = DataStore()
        self.prefs = Prefs()
        # 按屏幕尺寸收缩默认窗口大小，避免在小屏幕/VMware 下被摆到屏幕外
        try:
            screen = Gdk.Screen.get_default()
            sw = screen.get_width() if screen else 1100
            sh = screen.get_height() if screen else 720
        except Exception:  # noqa: BLE001
            sw, sh = 1100, 720
        w = max(640, min(1100, sw - 60))
        h = max(480, min(720, sh - 60))
        self.set_default_size(w, h)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.nav_map = {}       # name -> (button, stack_name)
        self.search_entry = None
        self.pending_ftype = None
        self.pending_screenshot = None

        self._build_ui()
        self._build_shortcuts()
        self.navigate("home")

    # ---------------------------------------------------------------- UI 搭建
    def _build_ui(self):
        self.get_style_context().add_class("app-window")

        # 顶部标题栏
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.get_style_context().add_class("app-header")
        title = Gtk.Label(label=APP_NAME)
        title.get_style_context().add_class("header-title")
        header.set_custom_title(title)

        # 搜索框
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("搜索反馈")
        self.search_entry.get_style_context().add_class("search-entry")
        self.search_entry.set_width_chars(28)
        self.search_entry.connect("activate", self._on_search_activate)
        header.pack_start(self.search_entry)

        # 快捷键帮助按钮
        help_btn = Gtk.Button(label="快捷键")
        help_btn.get_style_context().add_class("ghost-btn")
        help_btn.connect("clicked", lambda *_: self.show_shortcuts())
        header.pack_end(help_btn)

        self.set_titlebar(header)

        # 主体：侧边栏 + 内容栈
        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.add(root)

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar.get_style_context().add_class("nav-sidebar")
        sidebar.set_size_request(200, -1)
        root.pack_start(sidebar, False, False, 0)

        self.nav_group = None
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        root.pack_start(self.stack, True, True, 0)

        self._add_nav(sidebar, "home", "首页")
        self._add_nav(sidebar, "feedback", "反馈")
        self._add_nav(sidebar, "new", "新建反馈")
        self._add_nav(sidebar, "my", "我的反馈")
        self._add_nav(sidebar, "settings", "设置")

        # 页面交给 views 构建，先占位
        from . import views
        self.stack.add_named(views.build_home(self), "home")
        self.stack.add_named(views.build_feedback(self), "feedback")
        self.stack.add_named(views.build_new(self), "new")
        self.stack.add_named(views.build_my(self), "my")
        self.stack.add_named(views.build_settings(self), "settings")

    def _add_nav(self, sidebar, name, label):
        # 简单的"互斥"导航：用普通 Button 列表，自己维护 active 状态。
        # GTK3 中没有干净的方式让 ToggleButton 单选互斥，RadioButton 又会带圆点
        # 且 PyGObject 暴露的方法不一致；自己管状态最稳。
        btn = Gtk.Button(label=label)
        btn.get_style_context().add_class("nav-btn")
        btn.connect("clicked", self._on_nav_clicked, name)
        sidebar.pack_start(btn, False, False, 0)
        self.nav_map[name] = btn

    def _on_nav_clicked(self, btn, name):
        self.navigate(name)

    # ------------------------------------------------------------ 上下文方法
    def navigate(self, name):
        # 切换到指定页面：先取消所有 nav-btn 的 .active 标记，再给当前项加上。
        for n, b in self.nav_map.items():
            ctx = b.get_style_context()
            if n == name:
                ctx.add_class("active")
            else:
                ctx.remove_class("active")
        self.stack.set_visible_child_name(name)

    def show_detail(self, item_id):
        from . import views
        page = views.build_detail(self, item_id)
        self.stack.add_named(page, "detail")
        self.stack.set_visible_child_name("detail")
        # 让 detail 页可被返回
        self._detail_page = page

    def show_new(self, ftype=None):
        if ftype:
            self.pending_ftype = ftype
        else:
            self.pending_ftype = None
        self.navigate("new")

    def do_search(self, query):
        self.search_entry.set_text(query)
        self.navigate("feedback")
        views_refresh = self.stack.get_child_by_name("feedback")
        if hasattr(views_refresh, "refresh"):
            views_refresh.refresh()

    def paste_screenshot(self):
        """Ctrl+V：把剪贴板中的图片作为预览显示在新建反馈页。"""
        clip = self.get_clipboard()
        self.pending_screenshot = None
        try:
            pixbuf = clip.wait_for_image()
            if pixbuf is not None:
                self.pending_screenshot = pixbuf
        except Exception:
            self.pending_screenshot = None
        page = self.stack.get_child_by_name("new")
        if hasattr(page, "set_screenshot"):
            page.set_screenshot(self.pending_screenshot)

    # --------------------------------------------------------------- 快捷键
    def _build_shortcuts(self):
        # 每个动作对应一个 AccelPath，写入 Gtk.AccelMap，这样设置里可动态改绑。
        self.accel_group = Gtk.AccelGroup()
        self.add_accel_group(self.accel_group)

        self._accel_paths = {
            "search": "<Actions>/feedbackhub/search",
            "new": "<Actions>/feedbackhub/new",
            "home": "<Actions>/feedbackhub/home",
            "feedback": "<Actions>/feedbackhub/feedback",
            "my": "<Actions>/feedbackhub/my",
            "settings": "<Actions>/feedbackhub/settings",
            "submit": "<Actions>/feedbackhub/submit",
            "vote": "<Actions>/feedbackhub/vote",
            "back": "<Actions>/feedbackhub/back",
        }
        self._accel_handlers = {
            "search": self._accel_search,
            "new": self._accel_new,
            "home": self._accel_home,
            "feedback": self._accel_feedback,
            "my": self._accel_my,
            "settings": self._accel_settings,
            "submit": self._accel_submit,
            "vote": self._accel_vote,
            "back": self._accel_back,
        }

        # 为每个动作绑定一个可点击的加速键路径（实际激活通过 key-press 事件分发）
        for action, path in self._accel_paths.items():
            self._activate_accel_action(action, path)

        # 应用内：A 键为当前详情页投票（参照原版键盘操作）。
        # 输入框聚焦时不触发，避免打字误投票。
        self.connect("key-press-event", self._on_window_key)

    def _current_accel(self, action):
        """返回 (keyval, mods)，来自 prefs 中的快捷键字符串。"""
        accel = self.prefs.shortcuts.get(action, "")
        key, mods = Gtk.accelerator_parse(accel)
        return key, mods

    def _rebind_accel_path(self, action):
        """把某个动作的 AccelPath 重新映射到当前 prefs 中的快捷键。"""
        path = self._accel_paths[action]
        key, mods = self._current_accel(action)
        Gtk.AccelMap.change_entry(path, key, mods, True)

    def _activate_accel_action(self, action, path):
        key, mods = self._current_accel(action)
        Gtk.AccelMap.change_entry(path, key, mods, True)

    def rebind_shortcut(self, action, accel):
        """设置页调用：更新 prefs 并立即重绑快捷键。"""
        self.prefs.set_shortcut(action, accel)
        self._rebind_accel_path(action)

    def _resolve_action_from_key(self, event):
        """根据事件按键在 prefs 中反查命中的动作。"""
        key = Gdk.keyval_name(event.keyval)
        if not key:
            return None
        mods = event.state & (Gdk.ModifierType.CONTROL_MASK |
                              Gdk.ModifierType.MOD1_MASK |
                              Gdk.ModifierType.SHIFT_MASK)
        for action in self._accel_paths:
            k, m = self._current_accel(action)
            name = Gdk.keyval_name(k) if k else None
            if name and name.lower() == key.lower() and m == mods:
                return action
        return None

    def _on_window_key(self, widget, event):
        action = self._resolve_action_from_key(event)
        if action:
            focus = self.get_focus()
            # 输入框内按 Enter 等仍交由输入框处理，避免误触发
            if isinstance(focus, Gtk.Editable):
                if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_Escape):
                    return False
            handler = self._accel_handlers[action]
            if handler:
                return bool(handler())
        return False

    def _accel_search(self, *args):
        self.search_entry.grab_focus()
        return True

    def _accel_new(self, *args):
        self.show_new()
        return True

    def _accel_home(self, *args):
        self.navigate("home")
        return True

    def _accel_feedback(self, *args):
        self.navigate("feedback")
        return True

    def _accel_my(self, *args):
        self.navigate("my")
        return True

    def _accel_settings(self, *args):
        self.navigate("settings")
        return True

    def _accel_submit(self, *args):
        page = self.stack.get_visible_child()
        if self.stack.get_visible_child_name() == "new" and hasattr(page, "submit"):
            page.submit()
        return True

    def _accel_vote(self, *args):
        child = self.stack.get_visible_child()
        if self.stack.get_visible_child_name() == "detail" and hasattr(child, "vote_current"):
            child.vote_current()
        return True

    def _accel_back(self, *args):
        if self.stack.get_visible_child_name() == "detail":
            self.navigate("feedback")
        return True

    def _on_search_activate(self, entry):
        self.navigate("feedback")
        page = self.stack.get_child_by_name("feedback")
        if hasattr(page, "refresh"):
            page.refresh()

    # ------------------------------------------------------------ 快捷键说明
    def show_shortcuts(self):
        from .data import SHORTCUT_LABELS
        rows = []
        for action in self._accel_paths:
            if action in SHORTCUT_LABELS:
                accel = self.prefs.shortcuts.get(action, "")
                display = Gtk.accelerator_get_label(*Gtk.accelerator_parse(accel)) \
                    if accel else "未设置"
                rows.append((display, SHORTCUT_LABELS[action]))

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)
        for keys, desc in rows:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            k = Gtk.Label(label=keys)
            k.get_style_context().add_class("kbd-hint")
            d = Gtk.Label(label=desc, halign=Gtk.Align.START)
            row.pack_start(k, False, False, 0)
            row.pack_start(d, True, True, 0)
            box.pack_start(row, False, False, 0)

        dialog = Gtk.Dialog(title="快捷键", transient_for=self,
                            flags=Gtk.DialogFlags.MODAL)
        dialog.get_content_area().add(box)
        dialog.add_button("关闭", Gtk.ResponseType.OK)
        dialog.set_default_size(480, 360)
        dialog.show_all()
        dialog.run()
        dialog.destroy()


def _run_log(msg):
    """写运行日志到用户目录，便于排查"没报错但窗口不出现"。"""
    try:
        from .data import _data_dir
        with open(os.path.join(_data_dir(), "run.log"), "a",
                  encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:  # noqa: BLE001
        sys.stderr.write(msg + "\n")


def run():
    """经典 GTK 启动：Gtk.Window + Gtk.main()。

    不使用 Gtk.Application，规避 D-Bus 依赖（见 AppWindow 注释）。
    """
    _run_log("[feedbackhub] run() 开始")
    load_css()
    _run_log("[feedbackhub] CSS 加载完成")

    win = None
    try:
        win = AppWindow()
        _run_log("[feedbackhub] 窗口对象创建完成")
        win.connect("destroy", Gtk.main_quit)
        win.show_all()
        win.present()
        _run_log("[feedbackhub] show_all + present 完成")
    except Exception as e:  # noqa: BLE001
        import traceback
        _run_log("[feedbackhub] 窗口创建异常: %r\n%s"
                 % (e, traceback.format_exc()))
        sys.stderr.write("[feedbackhub] 窗口创建异常: %r\n%s\n"
                         % (e, traceback.format_exc()))
        return 1

    if win is None:
        return 1

    _run_log("[feedbackhub] 进入 Gtk.main()")
    Gtk.main()
    _run_log("[feedbackhub] Gtk.main() 退出")
    return 0


if __name__ == "__main__":
    sys.exit(run())