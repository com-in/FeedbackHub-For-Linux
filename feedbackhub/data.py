"""本地数据层：使用 JSON 在用户目录持久化所有反馈数据。

完全不涉及网络，所有读写都在本地完成。
"""
import json
import os
import sys
import time
import uuid


def _data_dir():
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "share")
    d = os.path.join(base, "feedbackhub")
    os.makedirs(d, exist_ok=True)
    return d


def _data_file():
    return os.path.join(_data_dir(), "feedback.json")


def _prefs_file():
    return os.path.join(_data_dir(), "prefs.json")


# 默认快捷键。键名对应 app.py 中的动作，值为 GTK 加速键字符串(<Control>F 等)。
DEFAULT_SHORTCUTS = {
    "search": "<Control>F",
    "new": "<Control>N",
    "home": "<Control>1",
    "feedback": "<Control>2",
    "my": "<Control>3",
    "settings": "<Control>4",
    "submit": "<Control>Return",
    "vote": "a",
    "back": "Escape",
}

# 动作的展示名（设置页用）
SHORTCUT_LABELS = {
    "search": "搜索反馈",
    "new": "新建反馈",
    "home": "前往首页",
    "feedback": "前往反馈列表",
    "my": "前往我的反馈",
    "settings": "前往设置",
    "submit": "提交反馈",
    "vote": "为反馈投票",
    "back": "返回上一页",
}


class Prefs:
    """用户偏好：目前仅保存自定义快捷键。"""

    def __init__(self):
        self.shortcuts = dict(DEFAULT_SHORTCUTS)
        self.load()

    def load(self):
        try:
            with open(_prefs_file(), "r", encoding="utf-8") as f:
                raw = json.load(f)
            saved = raw.get("shortcuts", {})
            # 只合并已知动作，忽略未知键
            for k in DEFAULT_SHORTCUTS:
                if saved.get(k):
                    self.shortcuts[k] = str(saved[k])
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass

    def save(self):
        try:
            data = {"shortcuts": self.shortcuts}
            tmp = _prefs_file() + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, _prefs_file())
        except OSError:
            pass

    def set_shortcut(self, action, accel):
        self.shortcuts[action] = accel
        self.save()


STATUSES = ["已收到", "正在调查", "需要更多信息", "已修复", "已实现", "已关闭"]

CATEGORIES = [
    ("桌面与应用", ["桌面", "开始菜单", "任务栏", "文件资源管理器", "窗口管理"]),
    ("系统", ["启动与关机", "更新", "安全", "账户", "设置"]),
    ("输入与设备", ["键盘", "鼠标", "触控板", "蓝牙", "打印机"]),
    ("显示与声音", ["显示", "声音", "显卡驱动"]),
    ("网络", ["有线网络", "无线网络", "蓝牙网络", "VPN"]),
    ("应用商店与应用", ["应用商店", "内置应用", "第三方应用"]),
    ("性能与可靠性", ["性能", "内存", "存储", "电池"]),
    ("游戏与图形", ["游戏", "图形性能", "DirectX"]),
    ("其他", ["其他"]),
]

PRODUCTS = ["Windows", "反馈中心", "Microsoft Edge", "照片", "终端", "其他产品"]

STATUS_COLORS = {
    "已收到": "#0078d4",
    "正在调查": "#f2c300",
    "需要更多信息": "#ff8c00",
    "已修复": "#107c10",
    "已实现": "#107c10",
    "已关闭": "#8a8a8a",
}


class FeedbackItem:
    def __init__(self, title="", description="", category="", subcategory="",
                 product="Windows", ftype="problem", status="已收到",
                 votes=0, comments=None, mine=False, blocked=False,
                 created=None, fid=None):
        self.id = fid or uuid.uuid4().hex[:12]
        self.title = title
        self.description = description
        self.category = category
        self.subcategory = subcategory
        self.product = product
        self.ftype = ftype  # problem | suggestion
        self.status = status
        self.votes = votes
        self.comments = comments if comments is not None else []
        self.mine = mine
        self.blocked = blocked
        self.created = created or time.time()

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "subcategory": self.subcategory,
            "product": self.product,
            "ftype": self.ftype,
            "status": self.status,
            "votes": self.votes,
            "comments": self.comments,
            "mine": self.mine,
            "blocked": self.blocked,
            "created": self.created,
        }

    @staticmethod
    def from_dict(d):
        return FeedbackItem(
            title=d.get("title", ""),
            description=d.get("description", ""),
            category=d.get("category", ""),
            subcategory=d.get("subcategory", ""),
            product=d.get("product", "Windows"),
            ftype=d.get("ftype", "problem"),
            status=d.get("status", "已收到"),
            votes=d.get("votes", 0),
            comments=d.get("comments", []),
            mine=d.get("mine", False),
            blocked=d.get("blocked", False),
            created=d.get("created", time.time()),
            fid=d.get("id"),
        )


def _seed():
    """预置一批示例反馈，让应用一打开就有内容可看（本地数据）。"""
    now = time.time()
    day = 86400
    items = [
        FeedbackItem(
            title="希望文件资源管理器支持多标签页",
            description="经常同时打开多个文件夹，标签页能大幅提升效率。",
            category="桌面与应用", subcategory="文件资源管理器",
            product="Windows", ftype="suggestion", status="已实现",
            votes=12843, created=now - 400 * day,
            comments=[
                {"author": "用户A", "text": "非常需要这个功能！", "ts": now - 300 * day},
                {"author": "用户B", "text": "支持，希望能尽快上线。", "ts": now - 250 * day},
            ],
        ),
        FeedbackItem(
            title="设置面板响应缓慢",
            description="打开设置后切换页面有明显卡顿，希望能优化性能。",
            category="系统", subcategory="设置",
            product="Windows", ftype="problem", status="正在调查",
            votes=3204, created=now - 60 * day,
            comments=[{"author": "用户C", "text": "我也遇到了，特别是在高DPI下。", "ts": now - 50 * day}],
        ),
        FeedbackItem(
            title="任务栏支持居中对齐",
            description="希望任务栏图标可以居中显示，类似平板模式下的样式。",
            category="桌面与应用", subcategory="任务栏",
            product="Windows", ftype="suggestion", status="已实现",
            votes=21560, created=now - 500 * day,
            comments=[{"author": "用户D", "text": "居中之后好看多了。", "ts": now - 400 * day}],
        ),
        FeedbackItem(
            title="蓝牙耳机偶发断连",
            description="使用蓝牙耳机时偶尔会出现声音断续或断开的情况。",
            category="输入与设备", subcategory="蓝牙",
            product="Windows", ftype="problem", status="需要更多信息",
            votes=877, created=now - 20 * day,
        ),
        FeedbackItem(
            title="希望内置截图工具支持录屏",
            description="截图工具如果能增加录屏功能会非常方便。",
            category="桌面与应用", subcategory="桌面",
            product="Windows", ftype="suggestion", status="已实现",
            votes=6540, created=now - 300 * day,
        ),
        FeedbackItem(
            title="夜间模式自动切换不生效",
            description="设置的自动切换时间段没有按预期生效。",
            category="显示与声音", subcategory="显示",
            product="Windows", ftype="problem", status="已修复",
            votes=412, created=now - 90 * day,
            comments=[{"author": "用户E", "text": "更新后已经正常了，谢谢！", "ts": now - 80 * day}],
        ),
        FeedbackItem(
            title="希望改进行动中心通知分组",
            description="通知太多时希望能按应用分组，方便查看。",
            category="桌面与应用", subcategory="桌面",
            product="Windows", ftype="suggestion", status="正在调查",
            votes=2210, created=now - 30 * day,
        ),
        FeedbackItem(
            title="开机启动速度偏慢",
            description="冷启动到桌面需要较长时间，希望优化启动流程。",
            category="性能与可靠性", subcategory="性能",
            product="Windows", ftype="problem", status="已收到",
            votes=1560, created=now - 10 * day,
        ),
    ]
    return [i.to_dict() for i in items]


class DataStore:
    def __init__(self):
        self.items = []
        self.voted = {}  # id -> bool
        self.load()

    def load(self):
        try:
            with open(_data_file(), "r", encoding="utf-8") as f:
                raw = json.load(f)
            self.items = [FeedbackItem.from_dict(d) for d in raw.get("items", [])]
            self.voted = raw.get("voted", {})
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            self.items = [FeedbackItem.from_dict(d) for d in _seed()]
            self.voted = {}
            self.save()

    def save(self):
        try:
            data = {
                "items": [i.to_dict() for i in self.items],
                "voted": self.voted,
            }
            tmp = _data_file() + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, _data_file())
        except OSError:
            pass

    def add_feedback(self, title, description, category, subcategory,
                     product, ftype, blocked=False, votes=1):
        item = FeedbackItem(
            title=title, description=description, category=category,
            subcategory=subcategory, product=product, ftype=ftype,
            status="已收到", votes=votes, mine=True, blocked=blocked,
        )
        self.items.append(item)
        self.save()
        return item

    def vote(self, item_id):
        if self.voted.get(item_id):
            return
        for it in self.items:
            if it.id == item_id:
                it.votes += 1
                self.voted[item_id] = True
                self.save()
                return

    def add_comment(self, item_id, text):
        for it in self.items:
            if it.id == item_id:
                it.comments.append(
                    {"author": "我", "text": text, "ts": time.time()})
                self.save()
                return

    def get(self, item_id):
        for it in self.items:
            if it.id == item_id:
                return it
        return None

    def my_items(self):
        return [i for i in self.items if i.mine]

    def search(self, query=""):
        q = query.strip().lower()
        if not q:
            return self.items
        return [i for i in self.items
                if q in i.title.lower() or q in i.description.lower()]


def main(*args):
    """占位，避免被误当作脚本执行。"""
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv))