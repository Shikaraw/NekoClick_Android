"""
NekoClick — 移动版自动点击器 (Kivy + AccessibilityService)
适用于 Android，通过无障碍服务模拟点击操作（无需 ADB、无需 Root）
"""
import os
import sys
import json
import threading
import time as time_module
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.progressbar import ProgressBar
from kivy.uix.stacklayout import StackLayout
from kivy.metrics import dp
from kivy.utils import platform
from kivy.graphics import Color, RoundedRectangle

# ─────────────────── 平台判断 ───────────────────
IS_ANDROID = platform == 'android'

if IS_ANDROID:
    try:
        from jnius import autoclass, cast
        # 获取 PythonActivity 上下文
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        current_activity = PythonActivity.mActivity
        Context = autoclass('android.content.Context')
        Intent = autoclass('android.content.Intent')
        Settings = autoclass('android.provider.Settings')
        Uri = autoclass('android.net.Uri')

        # 引用我们的无障碍服务
        NekoClickService = autoclass('org.nekoclick.NekoClickService')
        _as_available = True
    except Exception as e:
        print(f'[NekoClick] pyjnius 导入失败: {e}')
        _as_available = False
else:
    _as_available = False


# ─────────────────── 操作类型 ───────────────────
RADIOLIST = ['单击', '双击', '长按', '滑动', '延迟']
# 操作类型索引
OP_TAP = 0       # 单击
OP_DOUBLE = 1    # 双击
OP_LONG = 2      # 长按
OP_SWIPE = 3     # 滑动
OP_DELAY = 4     # 延迟
COORD_OPS = {OP_TAP, OP_DOUBLE, OP_LONG}
SWIPE_OPS = {OP_SWIPE}
DELAY_OPS = {OP_DELAY}
CMD_MAP = {
    'cl': OP_TAP, 'dc': OP_DOUBLE, 'lg': OP_LONG,
    'sw': OP_SWIPE, 'dl': OP_DELAY,
}
CMD_NAMES = {v: k for k, v in CMD_MAP.items()}


# ─────────────────── 无障碍服务工具 ───────────────────

def as_is_running() -> bool:
    """检查无障碍服务是否正在运行"""
    if not IS_ANDROID or not _as_available:
        return False
    try:
        return NekoClickService.isServiceRunning()
    except Exception:
        return False


def as_tap(x: int, y: int) -> bool:
    """通过无障碍服务模拟单击"""
    if not IS_ANDROID or not _as_available:
        return False
    try:
        return NekoClickService.tap(x, y)
    except Exception as e:
        print(f'[NekoClick] tap 失败: {e}')
        return False


def as_double_tap(x: int, y: int) -> bool:
    """通过无障碍服务模拟双击"""
    if not IS_ANDROID or not _as_available:
        return False
    try:
        return NekoClickService.doubleTap(x, y)
    except Exception as e:
        print(f'[NekoClick] doubleTap 失败: {e}')
        return False


def as_long_press(x: int, y: int, duration: int = 500) -> bool:
    """通过无障碍服务模拟长按"""
    if not IS_ANDROID or not _as_available:
        return False
    try:
        return NekoClickService.longPress(x, y, duration)
    except Exception as e:
        print(f'[NekoClick] longPress 失败: {e}')
        return False


def as_swipe(x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
    """通过无障碍服务模拟滑动"""
    if not IS_ANDROID or not _as_available:
        return False
    try:
        return NekoClickService.swipe(x1, y1, x2, y2, duration)
    except Exception as e:
        print(f'[NekoClick] swipe 失败: {e}')
        return False


def open_accessibility_settings():
    """打开无障碍设置页面"""
    if not IS_ANDROID or not _as_available:
        return
    try:
        intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        current_activity.startActivity(intent)
    except Exception as e:
        print(f'[NekoClick] 打开设置失败: {e}')


# ─────────────────── 样式常量 ───────────────────
COLOR_PRIMARY = '#1565C0'
COLOR_SUCCESS = '#2E7D32'
COLOR_WARN = '#E65100'
COLOR_DANGER = '#C62828'
COLOR_BG = '#F5F5F5'
COLOR_CARD = '#FFFFFF'


# ─────────────────── 主要 UI ───────────────────

class OpCard(BoxLayout):
    """一个操作组卡片"""

    def __init__(self, app, idx, **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None,
                         height=dp(120), padding=dp(8), spacing=dp(4))
        self.app = app
        self.idx = idx
        self.selected_op = 0
        self._setup_ui()

    def _setup_ui(self):
        # ── 第一行：操作类型按钮 ──
        btn_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(3))
        self.toggle_btns = []
        for i, name in enumerate(RADIOLIST):
            btn = ToggleButton(
                text=name, group=f'op_{self.idx}',
                size_hint_x=None, width=dp(56),
                font_size=dp(11),
                background_normal='',
                background_down='#4CAF50',
                color=(0.2, 0.2, 0.2, 1),
                on_press=lambda _, idx=i: self._on_select(idx)
            )
            btn_row.add_widget(btn)
            self.toggle_btns.append(btn)
        btn_row.add_widget(Label(size_hint_x=1))  # 弹性空间
        self.add_widget(btn_row)

        # ── 第二行：参数输入 + 操作按钮 ──
        param_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        self.param_area = BoxLayout(spacing=dp(4))
        param_row.add_widget(self.param_area)

        # 删除按钮
        del_btn = Button(
            text='✕', size_hint_x=None, width=dp(40),
            background_color=(0.9, 0.2, 0.2, 1),
            color=(1, 1, 1, 1), font_size=dp(16),
            on_press=lambda _: self.app.delete_group(self.idx)
        )
        param_row.add_widget(del_btn)
        self.add_widget(param_row)

        # 默认显示坐标输入
        self._show_coord_inputs()
        self.toggle_btns[0].state = 'down'

    def _on_select(self, op_idx):
        self.selected_op = op_idx
        self.param_area.clear_widgets()
        if op_idx in COORD_OPS:
            self._show_coord_inputs()
        elif op_idx in SWIPE_OPS:
            self._show_swipe_inputs()
        elif op_idx in DELAY_OPS:
            self._show_delay_inputs()

    def _show_coord_inputs(self):
        self.param_area.add_widget(Label(text='X:', size_hint_x=None, width=dp(20)))
        self.input_x = TextInput(text='', multiline=False, size_hint_x=None,
                                 width=dp(70), input_filter='int',
                                 font_size=dp(14), hint_text='0')
        self.param_area.add_widget(self.input_x)
        self.param_area.add_widget(Label(text='Y:', size_hint_x=None, width=dp(20)))
        self.input_y = TextInput(text='', multiline=False, size_hint_x=None,
                                 width=dp(70), input_filter='int',
                                 font_size=dp(14), hint_text='0')
        self.param_area.add_widget(self.input_y)

    def _show_swipe_inputs(self):
        self.param_area.add_widget(Label(text='X1:', size_hint_x=None, width=dp(22)))
        self.input_x1 = TextInput(text='', multiline=False, size_hint_x=None,
                                  width=dp(55), input_filter='int', font_size=dp(13))
        self.param_area.add_widget(self.input_x1)
        self.param_area.add_widget(Label(text='Y1:', size_hint_x=None, width=dp(22)))
        self.input_y1 = TextInput(text='', multiline=False, size_hint_x=None,
                                  width=dp(55), input_filter='int', font_size=dp(13))
        self.param_area.add_widget(self.input_y1)
        self.param_area.add_widget(Label(text='X2:', size_hint_x=None, width=dp(22)))
        self.input_x2 = TextInput(text='', multiline=False, size_hint_x=None,
                                  width=dp(55), input_filter='int', font_size=dp(13))
        self.param_area.add_widget(self.input_x2)
        self.param_area.add_widget(Label(text='Y2:', size_hint_x=None, width=dp(22)))
        self.input_y2 = TextInput(text='', multiline=False, size_hint_x=None,
                                  width=dp(55), input_filter='int', font_size=dp(13))
        self.param_area.add_widget(self.input_y2)

    def _show_delay_inputs(self):
        self.param_area.add_widget(Label(text='延迟 (秒):', size_hint_x=None, width=dp(70)))
        self.input_delay = TextInput(text='', multiline=False, size_hint_x=None,
                                     width=dp(70), input_filter='float',
                                     font_size=dp(14), hint_text='0.5')
        self.param_area.add_widget(self.input_delay)

    def get_params(self):
        """获取当前参数"""
        op = self.selected_op
        if op == OP_DELAY:
            try:
                t = float(self.input_delay.text)
                return op, t, None, None
            except ValueError:
                return op, None, None, None
        if op in COORD_OPS:
            try:
                x = int(self.input_x.text)
                y = int(self.input_y.text)
                return op, x, y, None
            except ValueError:
                return op, None, None, None
        if op in SWIPE_OPS:
            try:
                return (op,
                        int(self.input_x1.text), int(self.input_y1.text),
                        int(self.input_x2.text), int(self.input_y2.text))
            except ValueError:
                return op, None, None, None, None
        return op, None, None, None

    def set_params(self, op, *vals):
        """从加载数据恢复参数"""
        self.selected_op = op
        self.toggle_btns[op].state = 'down'
        self.param_area.clear_widgets()
        if op in COORD_OPS:
            self._show_coord_inputs()
            if len(vals) >= 2 and vals[0] is not None:
                self.input_x.text = str(vals[0])
                self.input_y.text = str(vals[1])
        elif op in SWIPE_OPS:
            self._show_swipe_inputs()
            if len(vals) >= 4:
                self.input_x1.text = str(vals[0])
                self.input_y1.text = str(vals[1])
                self.input_x2.text = str(vals[2])
                self.input_y2.text = str(vals[3])
        elif op == OP_DELAY:
            self._show_delay_inputs()
            if len(vals) >= 1 and vals[0] is not None:
                self.input_delay.text = str(vals[0])


# ─────────────────── 主应用 ───────────────────

class NekoClickApp(App):
    title = 'NekoClick'

    def build(self):
        Window.clearcolor = (0.96, 0.96, 0.96, 1)
        self.cards = []
        self._check_service()

        root = BoxLayout(orientation='vertical', spacing=dp(2))

        # ── 工具栏 ──
        toolbar = BoxLayout(size_hint_y=None, height=dp(54),
                            padding=[dp(6), dp(4)], spacing=dp(6))

        btn_data = [
            ('🎯 定位', '#1565C0', self._on_get_pos),
            ('▶ 执行', '#2E7D32', self._on_execute),
            ('💾 保存', '#E65100', self._on_save),
            ('📂 打开', '#6A1B9A', self._on_open),
            ('🔁 重复', '#00838F', self._on_repeat),
            ('🗑 清空', '#C62828', self._on_clear),
        ]
        for text, color, callback in btn_data:
            btn = Button(
                text=text, size_hint_x=None, width=dp(80),
                background_color=self._hex(color),
                color=(1, 1, 1, 1), font_size=dp(11),
                on_press=callback
            )
            toolbar.add_widget(btn)

        root.add_widget(toolbar)

        # ── 状态栏（服务状态） ──
        self.status_bar = Label(
            text=self.service_status, size_hint_y=None, height=dp(24),
            font_size=dp(10), color=(0.4, 0.4, 0.4, 1),
            halign='left', valign='middle'
        )
        self.status_bar.bind(size=self.status_bar.setter('text_size'))
        root.add_widget(self.status_bar)

        # ── 滚动操作区 ──
        self.scroll = ScrollView()
        self.card_container = BoxLayout(orientation='vertical',
                                        size_hint_y=None, spacing=dp(4),
                                        padding=[dp(6), dp(4)])
        self.card_container.bind(
            min_height=self.card_container.setter('height')
        )
        self.scroll.add_widget(self.card_container)
        root.add_widget(self.scroll)

        # ── 底部：新建按钮 ──
        bottom = BoxLayout(size_hint_y=None, height=dp(48), padding=[dp(6), dp(4)])
        add_btn = Button(
            text='＋ 新建操作', size_hint_x=None, width=dp(200),
            background_color=(0.3, 0.6, 0.3, 1), color=(1, 1, 1, 1),
            on_press=lambda _: self.add_card()
        )
        bottom.add_widget(add_btn)
        root.add_widget(bottom)

        # 添加第一个操作组
        Clock.schedule_once(lambda _: self.add_card(), 0.1)
        return root

    # ─────────── 工具方法 ───────────

    @staticmethod
    def _hex(h):
        h = h.lstrip('#')
        return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)) + (1,)

    def _check_service(self):
        """检查无障碍服务状态"""
        if not IS_ANDROID:
            self.service_ok = False
            self.service_status = '⚠️ 非 Android 环境，请在手机上运行'
            return

        if not _as_available:
            self.service_ok = False
            self.service_status = '❌ pyjnius 不可用，打包可能有问题'
            return

        running = as_is_running()
        if running:
            self.service_ok = True
            self.service_status = '✅ 无障碍服务运行中 ✓'
        else:
            self.service_ok = False
            self.service_status = '⚠️ 无障碍服务未开启，点击"设置"按钮开启'

    def _open_settings(self, _):
        """打开无障碍设置"""
        if IS_ANDROID:
            open_accessibility_settings()

    def _ensure_service(self) -> bool:
        """确保服务已开启，否则弹窗提示"""
        if self.service_ok:
            return True

        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(15))
        content.add_widget(Label(
            text='NekoClick 需要开启无障碍服务才能工作',
            size_hint_y=None, height=dp(30)
        ))
        content.add_widget(Label(
            text='请前往：设置 → 无障碍 → NekoClick → 开启服务',
            text_size=(dp(250), None), halign='center'
        ))

        btn_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        btn_row.add_widget(Button(
            text='前往设置', on_press=lambda _: (
                open_accessibility_settings(), popup.dismiss())
        ))
        btn_row.add_widget(Button(
            text='取消', on_press=lambda _: popup.dismiss()
        ))
        content.add_widget(btn_row)

        popup = Popup(title='需要无障碍服务', content=content,
                      size_hint=(0.8, 0.5))
        popup.open()
        return False

    # ─────────── 卡片管理 ───────────

    def add_card(self, op=0, *vals):
        idx = len(self.cards)
        card = OpCard(self, idx)
        if op != 0 or vals:
            card.set_params(op, *vals)
        self.cards.append(card)
        self.card_container.add_widget(card)
        self._refresh_indices()

    def delete_group(self, idx):
        if len(self.cards) <= 1:
            self._show_msg('提示', '至少保留一个操作')
            return
        card = self.cards.pop(idx)
        self.card_container.remove_widget(card)
        self._refresh_indices()

    def _refresh_indices(self):
        for i, card in enumerate(self.cards):
            card.idx = i
            for j, tb in enumerate(card.toggle_btns):
                tb.group = f'op_{i}'

    def _on_clear(self, _):
        self.cards.clear()
        self.card_container.clear_widgets()
        self.add_card()

    # ─────────── 执行 ───────────

    def _execute_op(self, op, *params):
        """执行单个操作"""
        if op == OP_TAP:
            return as_tap(params[0], params[1])
        elif op == OP_DOUBLE:
            return as_double_tap(params[0], params[1])
        elif op == OP_LONG:
            return as_long_press(params[0], params[1], 500)
        elif op == OP_SWIPE:
            return as_swipe(params[0], params[1], params[2], params[3], 300)
        elif op == OP_DELAY:
            time_module.sleep(params[0])
            return True
        return True

    def _on_execute(self, _):
        if not self._ensure_service():
            return
        if len(self.cards) == 0:
            self._show_msg('错误', '没有可执行的操作')
            return

        def run():
            success = 0
            fail = 0
            # 先检查一遍参数
            for i, card in enumerate(self.cards):
                op, *vals = card.get_params()
                if op == OP_DELAY:
                    if vals[0] is None:
                        Clock.schedule_once(
                            lambda _: self._show_msg('错误', f'第 {i + 1} 组延迟参数无效'))
                        fail += 1
                        continue
                    success += 1
                elif op in COORD_OPS:
                    x, y = vals[0], vals[1]
                    if x is None or y is None:
                        Clock.schedule_once(
                            lambda _: self._show_msg('错误', f'第 {i + 1} 组坐标参数无效'))
                        fail += 1
                        continue
                    success += 1
                elif op in SWIPE_OPS:
                    if any(v is None for v in vals[:4]):
                        Clock.schedule_once(
                            lambda _: self._show_msg('错误', f'第 {i + 1} 组滑动参数无效'))
                        fail += 1
                        continue
                    success += 1
                else:
                    success += 1

            # 实际执行
            executed = 0
            for i, card in enumerate(self.cards):
                op, *vals = card.get_params()
                if op == OP_DELAY and vals[0] is None:
                    continue
                if op in COORD_OPS and (vals[0] is None or vals[1] is None):
                    continue
                if op in SWIPE_OPS and any(v is None for v in vals[:4]):
                    continue

                try:
                    self._execute_op(op, *vals)
                    executed += 1
                except Exception as e:
                    Clock.schedule_once(
                        lambda _, e=e: self._show_msg('错误', str(e)))
                    fail += 1
                time_module.sleep(0.3)

            Clock.schedule_once(
                lambda _: self._show_msg('完成',
                    f'执行完毕！成功: {success}  失败: {fail}'))

        threading.Thread(target=run, daemon=True).start()

    def _on_repeat(self, _):
        if not self._ensure_service():
            return
        content = BoxLayout(orientation='vertical', spacing=dp(10),
                            padding=dp(20))
        content.add_widget(Label(text='重复执行次数:'))
        inp = TextInput(text='3', multiline=False, input_filter='int',
                        size_hint_y=None, height=dp(40))
        content.add_widget(inp)

        popup = Popup(title='重复执行', content=content,
                      size_hint=(0.6, 0.4), auto_dismiss=False)

        def do_repeat(_):
            try:
                count = int(inp.text)
            except ValueError:
                return
            popup.dismiss()

            def run():
                total_s = total_f = 0
                for r in range(count):
                    for card in self.cards:
                        op, *vals = card.get_params()
                        try:
                            self._execute_op(op, *vals)
                            total_s += 1
                        except:
                            total_f += 1
                        time_module.sleep(0.3)
                Clock.schedule_once(
                    lambda _: self._show_msg('重复完成',
                        f'重复 {count} 次\n成功: {total_s}  失败: {total_f}'))

            threading.Thread(target=run, daemon=True).start()

        btn_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        btn_row.add_widget(Button(text='开始', on_press=do_repeat,
                                  background_color=(0.3, 0.7, 0.3, 1),
                                  color=(1, 1, 1, 1)))
        btn_row.add_widget(Button(text='取消', on_press=lambda _: popup.dismiss()))
        content.add_widget(btn_row)
        popup.open()

    # ─────────── 获取位置 ───────────

    def _on_get_pos(self, _):
        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(8))
        content.add_widget(Label(text='请输入目标位置的坐标',
                                 size_hint_y=None, height=dp(30)))
        self.coord_label = Label(text='坐标: (---, ---)',
                                 size_hint_y=None, height=dp(30))
        content.add_widget(self.coord_label)

        popup = Popup(title='获取位置', content=content,
                      size_hint=(0.8, 0.5), auto_dismiss=False)

        input_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        input_row.add_widget(Label(text='X:', size_hint_x=None, width=dp(25)))
        inp_x = TextInput(text='', multiline=False, input_filter='int',
                          size_hint_x=None, width=dp(80))
        input_row.add_widget(inp_x)
        input_row.add_widget(Label(text='Y:', size_hint_x=None, width=dp(25)))
        inp_y = TextInput(text='', multiline=False, input_filter='int',
                          size_hint_x=None, width=dp(80))
        input_row.add_widget(inp_y)
        content.add_widget(input_row)

        def fill(_):
            try:
                x, y = int(inp_x.text), int(inp_y.text)
            except ValueError:
                self._show_msg('错误', '请输入有效坐标')
                return
            if self.cards:
                card = self.cards[-1]
                if card.selected_op in COORD_OPS:
                    card.input_x.text = str(x)
                    card.input_y.text = str(y)
            popup.dismiss()

        btn_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        btn_row.add_widget(Button(text='填入', on_press=fill,
                                  background_color=self._hex('#2E7D32'),
                                  color=(1, 1, 1, 1)))
        btn_row.add_widget(Button(text='取消', on_press=lambda _: popup.dismiss()))
        content.add_widget(btn_row)
        popup.open()

    # ─────────── 保存 / 加载 ───────────

    def _on_save(self, _):
        ops = []
        for card in self.cards:
            op, *vals = card.get_params()
            if op == OP_TAP:
                ops.append(f'cl({vals[0]},{vals[1]})')
            elif op == OP_DOUBLE:
                ops.append(f'dc({vals[0]},{vals[1]})')
            elif op == OP_LONG:
                ops.append(f'lg({vals[0]},{vals[1]})')
            elif op == OP_SWIPE:
                ops.append(f'sw({vals[0]},{vals[1]},{vals[2]},{vals[3]})')
            elif op == OP_DELAY:
                ops.append(f'dl({vals[0]})')

        text = ' '.join(ops)
        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(8))
        content.add_widget(Label(text='保存计划', font_size=dp(16)))
        content.add_widget(Label(text=f'预览: {text[:50]}...'))
        inp_path = TextInput(
            text=os.path.join(self.user_data_dir, 'plan.txt'),
            multiline=False, size_hint_y=None, height=dp(40))
        content.add_widget(inp_path)

        popup = Popup(title='保存', content=content,
                      size_hint=(0.8, 0.5), auto_dismiss=False)

        def do_save(_):
            path = inp_path.text
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(text)
                popup.dismiss()
                self._show_msg('成功', '保存成功！')
            except Exception as e:
                self._show_msg('错误', f'保存失败: {e}')

        btn_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        btn_row.add_widget(Button(text='保存', on_press=do_save,
                                  background_color=(0.3, 0.7, 0.3, 1),
                                  color=(1, 1, 1, 1)))
        btn_row.add_widget(Button(text='取消', on_press=lambda _: popup.dismiss()))
        content.add_widget(btn_row)
        popup.open()

    def _on_open(self, _):
        content = BoxLayout(orientation='vertical', padding=dp(10))
        file_chooser = FileChooserListView(
            path=self.user_data_dir,
            filters=['*.txt'],
            size_hint_y=0.8
        )
        content.add_widget(file_chooser)

        popup = Popup(title='打开计划', content=content,
                      size_hint=(0.9, 0.7), auto_dismiss=False)

        def do_open(_):
            if not file_chooser.selection:
                return
            path = file_chooser.selection[0]
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content_text = f.read().strip()
                self._load_from_text(content_text)
                popup.dismiss()
                self._show_msg('成功', '加载成功！')
            except Exception as e:
                self._show_msg('错误', f'加载失败: {e}')

        def do_cancel(_):
            popup.dismiss()

        btn_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        btn_row.add_widget(Button(text='打开', on_press=do_open))
        btn_row.add_widget(Button(text='取消', on_press=do_cancel))
        content.add_widget(btn_row)
        popup.open()

    def _load_from_text(self, text):
        self.cards.clear()
        self.card_container.clear_widgets()
        parts = text.split()
        for part in parts:
            part = part.strip()
            if not part:
                continue
            cmd = part[:2].lower()
            params_str = part[3:-1]
            op = CMD_MAP.get(cmd)
            if op is None:
                continue
            if cmd in ('cl', 'dc', 'lg'):
                parts_xy = params_str.split(',')
                x = int(parts_xy[0].strip())
                y = int(parts_xy[1].strip())
                self.add_card(op, x, y)
            elif cmd == 'sw':
                parts_xy = params_str.split(',')
                x1 = int(parts_xy[0].strip())
                y1 = int(parts_xy[1].strip())
                x2 = int(parts_xy[2].strip())
                y2 = int(parts_xy[3].strip())
                self.add_card(op, x1, y1, x2, y2)
            elif cmd == 'dl' and params_str:
                t = float(params_str.strip())
                self.add_card(op, t)

    # ─────────── 弹出消息 ───────────

    def _show_msg(self, title, msg):
        popup = Popup(title=title,
                      content=Label(text=msg, text_size=(dp(250), None)),
                      size_hint=(0.7, 0.3))
        popup.open()


# ─────────────────── 入口 ───────────────────
if __name__ == '__main__':
    NekoClickApp().run()
