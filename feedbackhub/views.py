"""所有页面视图：首页、反馈列表、新建反馈向导、我的反馈、详情、设置。

每个页面都是普通 Gtk 控件，通过上下文对象 ctx 访问数据与导航。
"""
import time

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Pango  # noqa: E402

from .data import CATEGORIES, PRODUCTS, STATUS_COLORS, STATUSES


# ---------------------------------------------------------------- 工具函数
def fmt_date(ts):
    return time.strftime("%Y/%m/%d", time.localtime(ts))


def badge(status):
    from gi.repository import Gdk
    lbl = Gtk.Label(label=status)
    lbl.get_style_context().add_class("badge")
    color = STATUS_COLORS.get(status, "#8a8a8a")
    rgba = Gdk.RGBA()
    rgba.parse(color)
    lbl.override_background_color(Gtk.StateFlags.NORMAL, rgba)
    return lbl


def make_vbox(spacing=0):
    return Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)


def scrolled_content():
    """返回 (ScrolledWindow, 内容vbox)。"""
    sw = Gtk.ScrolledWindow()
    sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    vbox = make_vbox(12)
    vbox.set_margin_top(8)
    vbox.set_margin_bottom(24)
    vbox.set_margin_start(28)
    vbox.set_margin_end(28)
    sw.add(vbox)
    return sw, vbox


def card(children):
    box = make_vbox(8)
    box.get_style_context().add_class("card")
    for c in children:
        box.pack_start(c, False, False, 0)
    return box


def title(text):
    lbl = Gtk.Label(label=text, xalign=0)
    lbl.get_style_context().add_class("page-title")
    return lbl


def subtitle(text):
    lbl = Gtk.Label(label=text, xalign=0)
    lbl.get_style_context().add_class("page-subtitle")
    lbl.set_margin_bottom(12)
    return lbl


def section(text):
    lbl = Gtk.Label(label=text, xalign=0)
    lbl.get_style_context().add_class("section-title")
    lbl.set_margin_top(8)
    return lbl


def _wrap_clickable(widget, on_click):
    evbox = Gtk.EventBox()
    evbox.add(widget)
    evbox.connect("button-press-event", lambda w, e: on_click())
    return evbox


def feedback_row(ctx, item):
    """单个反馈卡片，点击进入详情。"""
    top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    t = Gtk.Label(label=item.title, xalign=0, wrap=True)
    t.get_style_context().add_class("fb-title")
    top.pack_start(t, True, True, 0)
    top.pack_start(badge(item.status), False, False, 0)

    desc = Gtk.Label(
        label=item.description if item.description else "",
        xalign=0, wrap=True, ellipsize=Pango.EllipsizeMode.END)
    desc.get_style_context().add_class("fb-desc")
    desc.set_max_width_chars(90)

    meta = Gtk.Label(
        label="{} · {} · {}".format(
            item.product, item.category,
            "建议" if item.ftype == "suggestion" else "问题"),
        xalign=0)
    meta.get_style_context().add_class("fb-meta")

    stats = Gtk.Label(label="▲ {} · 💬 {} · {}".format(
        item.votes, len(item.comments), fmt_date(item.created)), xalign=0)
    stats.get_style_context().add_class("fb-stats")

    body = make_vbox(6)
    body.pack_start(top, False, False, 0)
    if item.description:
        body.pack_start(desc, False, False, 0)
    body.pack_start(meta, False, False, 0)
    body.pack_start(stats, False, False, 0)

    c = card([body])
    c.get_style_context().add_class("card-hover")
    return _wrap_clickable(c, lambda: ctx.show_detail(item.id))


def empty_state(icon, title_text, desc_text):
    box = make_vbox(6)
    box.set_margin_top(60)
    icon_lbl = Gtk.Label(label=icon)
    icon_lbl.set_markup('<span size="xx-large">%s</span>' % icon)
    t = Gtk.Label(label=title_text, xalign=0.5)
    t.get_style_context().add_class("empty-title")
    d = Gtk.Label(label=desc_text, wrap=True, justify=Gtk.Justification.CENTER)
    d.get_style_context().add_class("empty-desc")
    box.pack_start(icon_lbl, False, False, 0)
    box.pack_start(t, False, False, 0)
    box.pack_start(d, False, False, 0)
    return box


# ---------------------------------------------------------------- 首页
def build_home(ctx):
    sw, vbox = scrolled_content()
    vbox.pack_start(title("欢迎使用反馈中心"), False, False, 0)
    vbox.pack_start(subtitle("告诉我们你的想法，帮助我们改进体验。"), False, False, 0)

    # 两个大动作按钮
    actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
    actions.set_halign(Gtk.Align.FILL)
    problem = _big_action("⚠ 报告问题", "告诉我们哪里出了问题", Gtk.Orientation.VERTICAL)
    suggestion = _big_action("💡 建议新功能", "告诉我们你希望添加什么", Gtk.Orientation.VERTICAL)
    problem.connect("clicked", lambda *_: ctx.show_new("problem"))
    suggestion.connect("clicked", lambda *_: ctx.show_new("suggestion"))
    actions.pack_start(problem, True, True, 0)
    actions.pack_start(suggestion, True, True, 0)
    vbox.pack_start(actions, False, False, 0)

    # 分类快捷入口
    vbox.pack_start(section("选择一个分类"), False, False, 0)
    cat_box = Gtk.FlowBox(halign=Gtk.Align.FILL)
    cat_box.set_selection_mode(Gtk.SelectionMode.NONE)
    all_cats = [c[0] for c in CATEGORIES]
    for cat in all_cats:
        btn = Gtk.Button(label=cat)
        btn.get_style_context().add_class("ghost-btn")
        btn.connect("clicked", lambda w, name=cat: ctx.show_new())
        cat_box.add(btn)
    vbox.pack_start(cat_box, False, False, 0)

    # 最近反馈
    vbox.pack_start(section("最近反馈"), False, False, 0)
    recent = sorted(ctx.store.items, key=lambda i: i.created, reverse=True)[:4]
    for it in recent:
        vbox.pack_start(feedback_row(ctx, it), False, False, 0)
    vbox.pack_start(_footer(), False, False, 0)
    return sw


def _big_action(text, desc, orientation):
    box = Gtk.Button()
    inner = Gtk.Box(orientation=orientation, spacing=6)
    inner.set_margin_start(12)
    inner.set_margin_end(12)
    inner.set_margin_top(8)
    inner.set_margin_bottom(8)
    t = Gtk.Label(label=text, xalign=0 if orientation == Gtk.Orientation.HORIZONTAL else 0.5)
    t.get_style_context().add_class("fb-title")
    d = Gtk.Label(label=desc, xalign=0.5)
    d.get_style_context().add_class("action-desc")
    inner.pack_start(t, False, False, 0)
    inner.pack_start(d, False, False, 0)
    box.add(inner)
    box.get_style_context().add_class("big-action")
    return box


def _footer():
    lbl = Gtk.Label(
        label="反馈中心 · 本地版 %s\n所有反馈均保存在本设备，不会上传。"
              % __import__("feedbackhub").__version__,
        xalign=0)
    lbl.get_style_context().add_class("footer-text")
    lbl.set_margin_top(16)
    return lbl


# ---------------------------------------------------------------- 反馈列表
class FeedbackPage(Gtk.ScrolledWindow):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.inner = make_vbox(8)
        self.inner.set_margin_top(8)
        self.inner.set_margin_bottom(24)
        self.inner.set_margin_start(28)
        self.inner.set_margin_end(28)
        self.add(self.inner)

        self.product = Gtk.ComboBoxText()
        self.sort = Gtk.ComboBoxText()
        self._build_toolbar()
        self.refresh()

    def _build_toolbar(self):
        self.product.append_text("所有产品")
        for p in PRODUCTS:
            self.product.append_text(p)
        self.product.set_active(0)
        self.product.connect("changed", lambda *_: self.refresh())

        self.sort.append_text("最新")
        self.sort.append_text("最多投票")
        self.sort.set_active(0)
        self.sort.connect("changed", lambda *_: self.refresh())

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.get_style_context().add_class("card")
        lbl = Gtk.Label(label="产品:")
        lbl.get_style_context().add_class("fb-meta")
        box.pack_start(lbl, False, False, 0)
        box.pack_start(self.product, False, False, 0)
        slbl = Gtk.Label(label="排序:")
        slbl.get_style_context().add_class("fb-meta")
        box.pack_start(slbl, False, False, 0)
        box.pack_start(self.sort, False, False, 0)
        box.pack_start(Gtk.Label(), True, True, 0)
        self.inner.pack_start(title("反馈"), False, False, 0)
        self.inner.pack_start(box, False, False, 0)

    def refresh(self):
        # 清空旧列表
        for child in self.inner.get_children()[3:]:
            self.inner.remove(child)

        query = self.ctx.search_entry.get_text().strip()
        # 固定展示"没有反馈"：仅强制数据源为空，下方搜索/排序/产品过滤逻辑全部保留
        items = []
        prod = self.product.get_active_text()
        if prod and prod != "所有产品":
            items = [i for i in items if i.product == prod]

        if self.sort.get_active() == 1:
            items = sorted(items, key=lambda i: i.votes, reverse=True)
        else:
            items = sorted(items, key=lambda i: i.created, reverse=True)

        if query:
            self.inner.pack_start(subtitle("“%s” 的搜索结果" % query), False, False, 0)

        if not items:
            self.inner.pack_start(
                empty_state("🔍", "还没有反馈",
                            "报告问题或建议新功能后，会在这里看到。"),
                False, False, 0)
            return

        for it in items:
            self.inner.pack_start(feedback_row(self.ctx, it), False, False, 0)
        self.inner.pack_start(_footer(), False, False, 0)
        self.show_all()


def build_feedback(ctx):
    return FeedbackPage(ctx)


# ---------------------------------------------------------------- 我的反馈
class MyFeedbackPage(Gtk.ScrolledWindow):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.inner = make_vbox(12)
        self.inner.set_margin_top(8)
        self.inner.set_margin_bottom(24)
        self.inner.set_margin_start(28)
        self.inner.set_margin_end(28)
        self.add(self.inner)
        self.refresh()

    def refresh(self):
        for child in self.inner.get_children():
            self.inner.remove(child)
        self.inner.pack_start(title("我的反馈"), False, False, 0)
        self.inner.pack_start(subtitle("你提交的反馈及其最新状态。"), False, False, 0)
        items = self.ctx.store.my_items()
        if not items:
            self.inner.pack_start(
                empty_state("📭", "还没有反馈", "报告问题或建议新功能后，会在这里看到。"),
                False, False, 0)
            return
        for it in items:
            self.inner.pack_start(feedback_row(self.ctx, it), False, False, 0)
        self.show_all()


def build_my(ctx):
    return MyFeedbackPage(ctx)


# ---------------------------------------------------------------- 新建反馈（向导）
class NewFeedbackPage(Gtk.ScrolledWindow):
    STEPS = ["类型", "详情", "类似反馈", "类别", "提交"]

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.ftype = None
        self.title = Gtk.Entry()
        self.desc = Gtk.TextView()
        self.category = Gtk.ComboBoxText()
        self.subcategory = Gtk.ComboBoxText()
        self.product = Gtk.ComboBoxText()
        self.blocked = Gtk.CheckButton(label="将此视为阻塞性问题，急需处理")
        self.agree = Gtk.CheckButton(label="我同意将附带的文件随反馈一起处理")
        self.screenshot_pixbuf = None
        self.screenshot_box = None

        self.inner = make_vbox(12)
        self.inner.set_margin_top(8)
        self.inner.set_margin_bottom(24)
        self.inner.set_margin_start(28)
        self.inner.set_margin_end(28)
        self.add(self.inner)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self._build_step_type()
        self._build_step_detail()
        self._build_step_similar()
        self._build_step_category()
        self._build_step_confirm()
        self.inner.pack_start(self.stack, False, False, 0)

        btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btns.set_halign(Gtk.Align.END)
        self.back_btn = Gtk.Button(label="上一步")
        self.back_btn.get_style_context().add_class("ghost-btn")
        self.next_btn = Gtk.Button(label="下一步")
        self.next_btn.get_style_context().add_class("accent-btn")
        self.back_btn.connect("clicked", lambda *_: self._go(-1))
        self.next_btn.connect("clicked", lambda *_: self._go(1))
        btns.pack_start(self.back_btn, False, False, 0)
        btns.pack_start(self.next_btn, False, False, 0)
        self.inner.pack_start(btns, False, False, 0)

        self.progress = Gtk.Label(xalign=0)
        self.progress.get_style_context().add_class("fb-meta")
        self.inner.pack_start(self.progress, False, False, 0)

        self._set_step(0)
        self._apply_pending_type()

    # ---- 步骤定义
    def _build_step_type(self):
        box = make_vbox(12)
        box.set_halign(Gtk.Align.CENTER)
        box.set_margin_top(40)
        t = Gtk.Label(label="你想做什么？", xalign=0.5)
        t.get_style_context().add_class("page-title")
        box.pack_start(t, False, False, 0)
        p = Gtk.Button()
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        inner.set_margin_start(16); inner.set_margin_end(16)
        inner.set_margin_top(10); inner.set_margin_bottom(10)
        t1 = Gtk.Label(label="⚠ 报告问题", xalign=0.5)
        t1.get_style_context().add_class("fb-title")
        d1 = Gtk.Label(label="遇到了异常或错误行为", xalign=0.5)
        d1.get_style_context().add_class("action-desc")
        inner.pack_start(t1, False, False, 0)
        inner.pack_start(d1, False, False, 0)
        p.add(inner)
        p.get_style_context().add_class("big-action")
        p.connect("clicked", lambda *_: (setattr(self, "ftype", "problem"), self._go(1)))
        s = Gtk.Button()
        inner2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        inner2.set_margin_start(16); inner2.set_margin_end(16)
        inner2.set_margin_top(10); inner2.set_margin_bottom(10)
        t2 = Gtk.Label(label="💡 建议新功能", xalign=0.5)
        t2.get_style_context().add_class("fb-title")
        d2 = Gtk.Label(label="希望添加或改进的功能", xalign=0.5)
        d2.get_style_context().add_class("action-desc")
        inner2.pack_start(t2, False, False, 0)
        inner2.pack_start(d2, False, False, 0)
        s.add(inner2)
        s.get_style_context().add_class("big-action")
        s.connect("clicked", lambda *_: (setattr(self, "ftype", "suggestion"), self._go(1)))
        box.pack_start(p, False, False, 0)
        box.pack_start(s, False, False, 0)
        self.stack.add_named(box, "type")

    def _build_step_detail(self):
        box = make_vbox(8)
        box.pack_start(section("汇总你的反馈"), False, False, 0)
        self.title.set_placeholder_text("用一句话简要描述")
        self.title.get_style_context().add_class("text-input")
        box.pack_start(self.title, False, False, 0)
        box.pack_start(section("更详细地说明（可选）"), False, False, 0)
        self.desc.get_style_context().add_class("text-view")
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_size_request(-1, 180)
        sw.add(self.desc)
        box.pack_start(sw, False, False, 0)
        self.stack.add_named(box, "detail")

    def _build_step_similar(self):
        self.similar_box = make_vbox(8)
        self.similar_box.pack_start(section("查找类似反馈"), False, False, 0)
        self.similar_box.pack_start(
            subtitle("找到与你类似的反馈，可以点赞或继续提交新反馈。"),
            False, False, 0)
        self.stack.add_named(self.similar_box, "similar")

    def _build_step_category(self):
        box = make_vbox(8)
        box.pack_start(section("选择类别"), False, False, 0)
        for name, subcats in CATEGORIES:
            self.category.append_text(name)
        self.category.set_active(0)
        self.category.connect("changed", self._on_category_changed)
        box.pack_start(self.category, False, False, 0)
        box.pack_start(self.subcategory, False, False, 0)
        box.pack_start(section("产品"), False, False, 0)
        for p in PRODUCTS:
            self.product.append_text(p)
        self.product.set_active(0)
        box.pack_start(self.product, False, False, 0)
        self.stack.add_named(box, "category")

    def _build_step_confirm(self):
        box = make_vbox(8)
        box.pack_start(section("确认并提交"), False, False, 0)
        box.pack_start(subtitle("提交前请检查以下信息。"), False, False, 0)
        self.summary_lbl = Gtk.Label(xalign=0, wrap=True)
        self.summary_lbl.get_style_context().add_class("fb-desc")
        box.pack_start(self.summary_lbl, False, False, 0)

        # 附件区
        box.pack_start(section("附件"), False, False, 0)
        attach = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        paste_btn = Gtk.Button(label="📋 从剪贴板粘贴截图  (Ctrl+V)")
        paste_btn.get_style_context().add_class("ghost-btn")
        paste_btn.connect("clicked", lambda *_: self.ctx.paste_screenshot())
        attach.pack_start(paste_btn, False, False, 0)
        box.pack_start(attach, False, False, 0)
        self.screenshot_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.pack_start(self.screenshot_box, False, False, 0)

        box.pack_start(self.blocked, False, False, 0)
        box.pack_start(self.agree, False, False, 0)
        self.stack.add_named(box, "confirm")

    # ---- 逻辑
    def _on_category_changed(self, combo):
        self.subcategory.remove_all()
        idx = combo.get_active()
        if idx < 0:
            return
        for sc in CATEGORIES[idx][1]:
            self.subcategory.append_text(sc)
        self.subcategory.set_active(0)

    def _apply_pending_type(self):
        ft = self.ctx.__dict__.get("pending_ftype")
        if ft:
            self.ftype = ft
            self._go(1)

    def _set_step(self, idx):
        self.current = idx
        names = ["type", "detail", "similar", "category", "confirm"]
        self.stack.set_visible_child_name(names[idx])
        self.back_btn.set_sensitive(idx > 0)
        if idx == len(names) - 1:
            self.next_btn.set_label("提交  (Ctrl+Enter)")
        else:
            self.next_btn.set_label("下一步")
        if idx == 0:
            self.back_btn.set_sensitive(False)
        self.progress.set_text("步骤 %d / %d：%s" % (idx + 1, len(names), self.STEPS[idx]))

    def _go(self, delta):
        next_idx = self.current + delta
        if next_idx < 0:
            return
        if delta > 0:
            if not self._validate(self.current):
                return
            if self.current == 1:
                self._populate_similar()
        if delta < 0:
            pass
        if next_idx >= len(self.STEPS):
            self.submit()
            return
        self._set_step(next_idx)

    def _validate(self, idx):
        if idx == 1:  # detail
            if not self.title.get_text().strip():
                self._flash("请先填写反馈汇总。")
                return False
            return True
        if idx == 3:  # category
            return True
        if idx == 4:  # confirm
            if not self.agree.get_active():
                self._flash("请勾选同意处理附带的文件。")
                return False
            return True
        return True

    def _flash(self, msg):
        self.progress.set_text("⚠ " + msg)

    def _populate_similar(self):
        for child in self.similar_box.get_children()[2:]:
            self.similar_box.remove(child)
        q = self.title.get_text().strip()
        results = self.ctx.store.search(q)[:3] if q else []
        if not results:
            info = Gtk.Label(
                label="没有找到明显相似的反馈，可以放心提交新反馈。",
                xalign=0)
            info.get_style_context().add_class("fb-desc")
            self.similar_box.pack_start(info, False, False, 0)
        else:
            for it in results:
                self.similar_box.pack_start(feedback_row(self.ctx, it), False, False, 0)
        self.similar_box.show_all()

    def set_screenshot(self, pixbuf):
        self.screenshot_pixbuf = pixbuf
        for child in self.screenshot_box.get_children():
            self.screenshot_box.remove(child)
        if pixbuf is not None:
            img = Gtk.Image.new_from_pixbuf(pixbuf)
            self.screenshot_box.pack_start(img, False, False, 0)
            self.screenshot_box.show_all()

    def submit(self):
        if not self._validate(4):
            return
        title = self.title.get_text().strip()
        buf = self.desc.get_buffer()
        desc = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False).strip()
        cat = self.category.get_active_text() or "其他"
        sub = self.subcategory.get_active_text() or ""
        prod = self.product.get_active_text() or "Linux"
        blocked = self.blocked.get_active()
        item = self.ctx.store.add_feedback(
            title=title, description=desc, category=cat, subcategory=sub,
            product=prod, ftype=self.ftype or "problem", blocked=blocked)
        # 重置向导
        self.title.set_text("")
        self.desc.get_buffer().set_text("")
        self.ftype = None
        self.screenshot_pixbuf = None
        self.ctx.pending_ftype = None
        self._set_step(0)
        self.ctx.navigate("my")


def build_new(ctx):
    return NewFeedbackPage(ctx)


# ---------------------------------------------------------------- 详情
class FeedbackDetail(Gtk.ScrolledWindow):
    def __init__(self, ctx, item):
        super().__init__()
        self.ctx = ctx
        self.item = item
        self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.inner = make_vbox(12)
        self.inner.set_margin_top(8)
        self.inner.set_margin_bottom(24)
        self.inner.set_margin_start(28)
        self.inner.set_margin_end(28)
        self.add(self.inner)
        self.vote_btn = None
        self._build()

    def _build(self):
        it = self.item
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        t = Gtk.Label(label=it.title, xalign=0, wrap=True)
        t.get_style_context().add_class("page-title")
        top.pack_start(t, True, True, 0)
        top.pack_start(badge(it.status), False, False, 0)
        self.inner.pack_start(top, False, False, 0)

        meta = Gtk.Label(label="{} · {} · {} · {}".format(
            self.ctx.store.voted.get(it.id, False) and "已投票" or "待投票",
            it.product, it.category, fmt_date(it.created)), xalign=0)
        meta.get_style_context().add_class("fb-meta")
        self.inner.pack_start(meta, False, False, 0)

        if it.description:
            d = Gtk.Label(label=it.description, xalign=0, wrap=True)
            d.get_style_context().add_class("fb-desc")
            self.inner.pack_start(d, False, False, 0)

        # 投票按钮
        self.vote_btn = Gtk.Button()
        self._update_vote_label()
        self.vote_btn.get_style_context().add_class("vote-btn")
        self.vote_btn.connect("clicked", lambda *_: self.vote_current())
        self.inner.pack_start(self.vote_btn, False, False, 0)

        # 评论
        self.inner.pack_start(section("评论 (%d)" % len(it.comments)), False, False, 0)
        for c in it.comments:
            self.inner.pack_start(self._comment_card(c), False, False, 0)

        # 添加评论
        add = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.comment_entry = Gtk.Entry()
        self.comment_entry.set_placeholder_text("添加评论…")
        self.comment_entry.get_style_context().add_class("text-input")
        self.comment_entry.connect("activate", lambda *_: self._add_comment())
        send = Gtk.Button(label="评论")
        send.get_style_context().add_class("accent-btn")
        send.connect("clicked", lambda *_: self._add_comment())
        add.pack_start(self.comment_entry, True, True, 0)
        add.pack_start(send, False, False, 0)
        self.inner.pack_start(add, False, False, 0)

    def _comment_card(self, c):
        box = make_vbox(4)
        box.get_style_context().add_class("card")
        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        a = Gtk.Label(label=c.get("author", "用户"), xalign=0)
        a.get_style_context().add_class("comment-author")
        dt = Gtk.Label(label=fmt_date(c.get("ts", time.time())), xalign=1)
        dt.get_style_context().add_class("comment-date")
        head.pack_start(a, False, False, 0)
        head.pack_start(Gtk.Label(), True, True, 0)
        head.pack_start(dt, False, False, 0)
        box.pack_start(head, False, False, 0)
        txt = Gtk.Label(label=c.get("text", ""), xalign=0, wrap=True)
        txt.get_style_context().add_class("comment-text")
        box.pack_start(txt, False, False, 0)
        return box

    def _update_vote_label(self):
        voted = self.ctx.store.voted.get(self.item.id, False)
        self.vote_btn.set_label("%s %d 人需要此反馈" % ("✓" if voted else "▲", self.item.votes))
        if voted:
            self.vote_btn.get_style_context().add_class("voted")

    def vote_current(self):
        self.ctx.store.vote(self.item.id)
        self._update_vote_label()

    def _add_comment(self):
        text = self.comment_entry.get_text().strip()
        if not text:
            return
        self.ctx.store.add_comment(self.item.id, text)
        self.comment_entry.set_text("")
        self.refresh()

    def refresh(self):
        for child in self.inner.get_children():
            self.inner.remove(child)
        self._build()
        self.show_all()


def build_detail(ctx, item_id):
    item = ctx.store.get(item_id)
    if item is None:
        return empty_state("❓", "未找到该反馈", "它可能已被移除。")
    return FeedbackDetail(ctx, item)


# ---------------------------------------------------------------- 设置
def build_settings(ctx):
    sw, vbox = scrolled_content()
    vbox.pack_start(title("设置"), False, False, 0)
    vbox.pack_start(subtitle("管理反馈中心的偏好。"), False, False, 0)

    row = card([
        _setting("数据存储", "所有反馈保存在本设备：~/.local/share/feedbackhub/"),
        _setting("主题", "跟随系统外观（浅色 / 深色）。"),
        _setting("版本", "反馈中心 1.0.0（本地版）"),
    ])
    vbox.pack_start(row, False, False, 0)

    # 快捷键自定义
    kb_title = Gtk.Label(label="快捷键", xalign=0)
    kb_title.get_style_context().add_class("setting-name")
    kb = card([kb_title] + _shortcut_rows(ctx))
    vbox.pack_start(kb, False, False, 0)

    from .data import SHORTCUT_LABELS
    hint = Gtk.Label(label="点击右侧“更改”可为对应操作设置新的快捷键；"
                           "完成后按 Esc 关闭，快捷键立即生效。",
                     xalign=0, wrap=True)
    hint.get_style_context().add_class("setting-desc")
    vbox.pack_start(hint, False, False, 0)

    vbox.pack_start(_footer(), False, False, 0)
    return sw


def _shortcut_rows(ctx):
    """为每个可自定义的动作生成一行：名称 + 当前快捷键 + 更改按钮。"""
    from gi.repository import Gdk
    from .data import SHORTCUT_LABELS

    rows = []
    prefs = ctx.prefs
    for action, label in SHORTCUT_LABELS.items():
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        name = Gtk.Label(label=label, xalign=0)
        name.get_style_context().add_class("setting-name")
        name.set_hexpand(True)
        box.pack_start(name, True, True, 0)

        accel = prefs.shortcuts.get(action, "")
        key, mods = Gtk.accelerator_parse(accel)
        cur = Gtk.Label(label=Gtk.accelerator_get_label(key, mods) if accel else "未设置")
        cur.get_style_context().add_class("kbd-hint")
        box.pack_start(cur, False, False, 0)

        btn = Gtk.Button(label="更改")
        btn.get_style_context().add_class("ghost-btn")
        btn.connect("clicked", _on_change_shortcut, ctx, action, cur)
        box.pack_start(btn, False, False, 0)

        rows.append(box)
    return rows


def _on_change_shortcut(btn, ctx, action, current_label):
    from gi.repository import Gdk

    # 捕获按键对话框：用户按下要绑定的组合键
    dialog = Gtk.Dialog(title="更改快捷键", transient_for=ctx,
                        flags=Gtk.DialogFlags.MODAL)
    dialog.set_default_size(360, 120)
    area = dialog.get_content_area()
    area.set_margin_top(16)
    area.set_margin_bottom(16)
    area.set_margin_start(16)
    area.set_margin_end(16)

    tip = Gtk.Label(label="请按下新的快捷键组合（例如 Ctrl+Shift+B）",
                    xalign=0)
    area.pack_start(tip, False, False, 0)

    status = Gtk.Label(label="")
    status.get_style_context().add_class("setting-desc")
    area.pack_start(status, False, False, 0)

    res = {"accel": None}
    def on_key(widget, event):
        # 忽略纯修饰键
        if event.keyval in (Gdk.KEY_Control_L, Gdk.KEY_Control_R,
                            Gdk.KEY_Shift_L, Gdk.KEY_Shift_R,
                            Gdk.KEY_Alt_L, Gdk.KEY_Alt_R,
                            Gdk.KEY_Super_L, Gdk.KEY_Super_R):
            return False
        if event.keyval == Gdk.KEY_Escape:
            dialog.response(Gtk.ResponseType.CANCEL)
            return True
        keyname = Gdk.keyval_name(event.keyval)
        mods = event.state & (Gdk.ModifierType.CONTROL_MASK |
                              Gdk.ModifierType.MOD1_MASK |
                              Gdk.ModifierType.SHIFT_MASK |
                              Gdk.ModifierType.SUPER_MASK)
        accel = Gtk.accelerator_name(Gdk.keyval_from_name(keyname), mods)
        res["accel"] = accel
        status.set_text("已捕获: " + Gtk.accelerator_get_label(
            Gdk.keyval_from_name(keyname), mods))
        dialog.response(Gtk.ResponseType.OK)
        return True

    dialog.connect("key-press-event", on_key)
    dialog.add_button("取消", Gtk.ResponseType.CANCEL)
    dialog.show_all()
    resp = dialog.run()
    dialog.destroy()

    if resp == Gtk.ResponseType.OK and res["accel"]:
        ctx.rebind_shortcut(action, res["accel"])
        key, mods = Gtk.accelerator_parse(res["accel"])
        current_label.set_text(Gtk.accelerator_get_label(key, mods))


def _setting(name, desc):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    n = Gtk.Label(label=name, xalign=0)
    n.get_style_context().add_class("setting-name")
    d = Gtk.Label(label=desc, xalign=0, wrap=True)
    d.get_style_context().add_class("setting-desc")
    box.pack_start(n, False, False, 0)
    box.pack_start(d, False, False, 0)
    return box