#!/usr/bin/env python3
"""反馈中心诊断脚本：不启动 GUI，逐项检测运行环境并打印结果。

用法:  python3 /usr/lib/feedbackhub/diagnose.py
"""
import os
import sys
import time
import traceback


def section(t):
    print("\n===== %s =====" % t)


def main():
    print("=== 反馈中心诊断脚本 ===")
    section("基本环境")
    print("python    : %s (%s)" % (sys.executable, sys.version.split()[0]))
    print("HOME      : %r" % os.environ.get("HOME"))
    print("DISPLAY   : %r" % os.environ.get("DISPLAY"))
    print("WAYLAND   : %r" % os.environ.get("WAYLAND_DISPLAY"))
    print("SESSION   : %r" % os.environ.get("XDG_SESSION_TYPE"))
    print("DBUS_ADDR : %r" % os.environ.get("DBUS_SESSION_BUS_ADDRESS"))

    section("GTK 绑定导入")
    try:
        import gi
        print("gi 导入 OK")
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk, Gdk, GLib  # noqa
        print("Gtk 版本: %d.%d.%d" % (
            Gtk.get_major_version(), Gtk.get_minor_version(),
            Gtk.get_micro_version()))
    except Exception as e:  # noqa: BLE001
        print("GTK 导入失败（应用无法启动的直接原因）: %r" % (e,))
        traceback.print_exc()
        sys.exit(1)

    section("显示服务器")
    try:
        screen = Gdk.Screen.get_default()
        if screen is None:
            print("Gdk.Screen.get_default() 返回 None —— 无图形会话，窗口无法显示")
        else:
            print("屏幕: %dx%d" % (screen.get_width(), screen.get_height()))
    except Exception as e:  # noqa: BLE001
        print("Gdk.Screen 异常: %r" % (e,))
        traceback.print_exc()

    section("数据目录写入（run.log 是否可写）")
    try:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(
            os.path.expanduser("~"), ".local", "share")
        d = os.path.join(base, "feedbackhub")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "diag.tmp")
        with open(p, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(p)
        print("可写: %s" % d)
    except Exception as e:  # noqa: BLE001
        print("不可写（这就是没有 run.log 的原因）: %r" % (e,))

    section("真实窗口创建测试（1.5 秒后自动关闭）")
    try:
        win = Gtk.Window(title="反馈中心-诊断")
        win.set_default_size(400, 300)
        win.show_all()
        win.realize()
        gdkwin = win.get_window()
        print("窗口 realize 成功")
        print("GdkWindow 是否存在 : %s" % ("是" if gdkwin else "否"))
        if gdkwin is not None:
            print("GdkWindow 可见     : %s" % ("是" if gdkwin.is_viewable() else "否"))
        print("窗口 is_visible    : %s" % ("是" if win.get_visible() else "否"))
        GLib.timeout_add(1500, Gtk.main_quit)
        Gtk.main()
        print("主循环正常退出")
    except Exception as e:  # noqa: BLE001
        print("窗口创建/显示异常（窗口弹不出的直接原因）: %r" % (e,))
        traceback.print_exc()

    print("\n===== 诊断结束 =====")


if __name__ == "__main__":
    main()
