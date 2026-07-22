"""
NekoClick — 移动版自动点击器 (Kivy)
适用于 Android，通过 ADB 执行点击操作
"""
import os
import sys
import json
import subprocess
import threading
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

# ─────────────────── 操作类型 ───────────────────
RADIOLIST = ['单击', '双击', '右键', '移动', '按下', '释放', '延迟']
COORD_OPS = {0, 1, 2, 3, 4}
DELAY_OPS = {6}
CMD_MAP = {
    'cl': 0, 'dc': 1, 'rc': 2,
    'mv': 3, 'pd': 4, 'rl': 5, 'dl': 6,
}
CMD_NAMES = {v: k for k, v in CMD_MAP.items()}

# ─────────────────── ADB 工具 ───────────────────
def adb_available() -> bool:
    """检查 ADB 是否可用"""
    try:
        subprocess.run(['adb', 'version'],
                       capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def adb_devices() -> list:
    """获取已连接的设备列表"""
    try:
        r = subprocess.run(['adb', 'devices'],
                           capture_output=True, text=True, timeout=5)
        lines = r.stdout.strip().split('\n')[1:]
        devices = []
        for line in lines:
            if line.strip() and 'device' in line and 'offline' not in line:
                devices.append(line.split()[0])
        return devices
    except Exception:
        return []


def adb_tap(x: int, y: int, device: str = ''):
    """通过 ADB 模拟点击"""
    cmd = ['adb']
    if device:
        cmd += ['-s', device]
    cmd += ['shell', 'input', 'tap', str(x), str(y)]
    subprocess.run(cmd, capture_output=True, timeout=10)


def adb_swipe(x1, y1, x2, y2, duration=300, device: str = ''):
    """通过 ADB 模拟滑动"""
    cmd = ['adb']
    if device:
        cmd += ['-s', device]
    cmd += ['shell', 'input', 'swipe', str(x1), str(y1), str(x2), str(y2), str(duration)]
    subprocess.run(cmd, capture_output=True, timeout=10)


def adb_screencap(device: str = '') -> bytes:
    """截取屏幕（返回 PNG 字节）"""
    cmd = ['adb']
    if device:
        cmd += ['-s', device]
    cmd += ['exec-out', 'screencap', '-p']
    r = subprocess.run(cmd, capture_output=True, timeout=15)
    return r.stdout


def get_screen_size(device: str = '') -> tuple:
    """获取设备屏幕尺寸"""
    cmd = ['adb']
    if device:
        cmd += ['-s', device]
    cmd += ['shell', 'wm', 'size']
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        text = r.stdout.strip()
        if 'x' in text:
            parts = text.split()[-1].split('x')
            return int(parts[0]), int(parts[1])
    except Exception:
        pass
    return 1080, 1920  # 默认值


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
        elif op_idx in DELAY_OPS:
            self._show_delay_inputs()
        # Release (5) 不显示输入

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

    def _show_delay_inputs(self):
        self.param_area.add_widget(Label(text='延迟 (秒):', size_hint_x=None, width=dp(70)))
        self.input_delay = TextInput(text='', multiline=False, size_hint_x=None,
                                     width=dp(70), input_filter='float',
                                     font_size=dp(14), hint_text='0.5')
        self.param_area.add_widget(self.input_delay)

    def get_params(self):
        """获取当前参数"""
        op = self.selected_op
        if op == 5:  # Release
            return op, None, None
        if op == 6:  # Delay
            try:
                t = float(self.input_delay.text)
                return op, t, None
            except ValueError:
                return op, None, None
        if op in COORD_OPS:
            try:
                x = int(self.input_x.text)
                y = int(self.input_y.text)
                return op, x, y
            except ValueError:
                return op, None, None
        return op, None, None

    def set_params(self, op, val1, val2):
        """从加载数据恢复参数"""
        self.selected_op = op
        self.toggle_btns[op].state = 'down'
        self.param_area.clear_widgets()
        if op in COORD_OPS:
            self._show_coord_inputs()
            if val1 is not None:
                self.input_x.text = str(val1)
            if val2 is not None:
                self.input_y.text = str(val2)
        elif op == 6:
            self._show_delay_inputs()
            if val1 is not None:
                self.input_delay.text = str(val1)


# ─────────────────── 主应用 ───────────────────

class NekoClickApp(App):
    title = 'NekoClick'

    def build(self):
        Window.clearcolor = (0.96, 0.96, 0.96, 1)
        self.cards = []
        self._check_adb()

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

        # ── 状态栏（ADB 状态） ──
        self.status_bar = Label(
            text=self.adb_status, size_hint_y=None, height=dp(24),
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
        """'#RRGGBB' → (r/255, g/255, b/255, 1)"""
        h = h.lstrip('#')
        return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)) + (1,)

    def _check_adb(self):
        if platform == 'android':
            # Android 上尝试内置 ADB 或使用 /system/bin/
            self.adb_ok = True
            self.adb_status = '📱 Android 模式（使用系统触控 API）'
        else:
            self.adb_ok = adb_available()
            if self.adb_ok:
                devices = adb_devices()
                if devices:
                    self.adb_status = f'✅ ADB 已连接 | 设备: {devices[0]}'
                else:
                    self.adb_status = '⚠️ ADB 可用，但无设备连接'
            else:
                self.adb_status = '❌ ADB 未安装，请安装 ADB 并连接手机'

    def _get_device(self):
        devices = adb_devices()
        return devices[0] if devices else ''

    # ─────────── 卡片管理 ───────────

    def add_card(self, op=0, val1=None, val2=None):
        idx = len(self.cards)
        card = OpCard(self, idx)
        if op != 0 or val1 is not None:
            card.set_params(op, val1, val2)
        self.cards.append(card)
        self.card_container.add_widget(card)
        # 刷新所有 card 引用
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
            # 更新 ToggleButton 的 group
            for j, tb in enumerate(card.toggle_btns):
                tb.group = f'op_{i}'

    def _on_clear(self, _):
        self.cards.clear()
        self.card_container.clear_widgets()
        self.add_card()

    # ─────────── 执行 ───────────

    def _execute_op(self, op, p1, p2):
        if platform == 'android':
            self._show_msg('提示', 'Android 原生执行模式尚未实现，'
                                  '请使用 ADB 连接电脑运行')
            return
        if not self.adb_ok:
            self._show_msg('错误', 'ADB 不可用，无法执行操作')
            return
        device = self._get_device()
        if op == 0:
            adb_tap(p1, p2, device)
        elif op == 1:
            adb_tap(p1, p2, device)
            import time
            time.sleep(0.1)
            adb_tap(p1, p2, device)
        elif op == 2:
            adb_tap(p1, p2, device)
        elif op == 3:
            # 移动到目标（adb 没有直接 moveTo，用 swipe 0px 模拟）
            adb_swipe(p1, p2, p1, p2, 200, device)
        elif op == 4:
            # press down: 按下不放
            subprocess.run(
                ['adb'] + (['-s', device] if device else [])
                + ['shell', 'input', 'swipe', str(p1), str(p2),
                   str(p1), str(p2), '2000'],
                capture_output=True, timeout=15
            )
        elif op == 5:
            # release: 模拟抬起（发送一个小距离的 swipe 模拟释放）
            pass
        elif op == 6:
            import time
            time.sleep(p1)

    def _on_execute(self, _):
        if len(self.cards) == 0:
            self._show_msg('错误', '没有可执行的操作')
            return

        def run():
            success = 0
            fail = 0
            for i, card in enumerate(self.cards):
                op, p1, p2 = card.get_params()
                if op == 5:
                    success += 1
                    continue
                if p1 is None:
                    Clock.schedule_once(
                        lambda _: self._show_msg('错误', f'第 {i + 1} 组参数无效'))
                    fail += 1
                    continue
                try:
                    self._execute_op(op, p1, p2)
                    success += 1
                except Exception as e:
                    Clock.schedule_once(
                        lambda _, e=e: self._show_msg('错误', str(e)))
                    fail += 1
                import time
                time.sleep(0.3)

            Clock.schedule_once(
                lambda _: self._show_msg('完成',
                                         f'执行完毕！成功: {success}  失败: {fail}'))

        threading.Thread(target=run, daemon=True).start()

    def _on_repeat(self, _):
        # 弹出次数输入
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
                    for i, card in enumerate(self.cards):
                        op, p1, p2 = card.get_params()
                        if op == 5 or p1 is None:
                            if op == 5:
                                total_s += 1
                            else:
                                total_f += 1
                            continue
                        try:
                            self._execute_op(op, p1, p2)
                            total_s += 1
                        except:
                            total_f += 1
                        import time
                        time.sleep(0.3)
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
        if not self.adb_ok and platform != 'android':
            self._show_msg('错误', 'ADB 不可用，无法获取位置')
            return

        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(8))
        self.pos_label = Label(text='点击「截图」后，在图片上点选位置',
                               size_hint_y=None, height=dp(30))
        content.add_widget(self.pos_label)
        self.coord_label = Label(text='坐标: (---, ---)',
                                 size_hint_y=None, height=dp(30))
        content.add_widget(self.coord_label)

        popup = Popup(title='获取位置', content=content,
                      size_hint=(0.8, 0.7), auto_dismiss=False)

        def capture(_):
            if platform == 'android':
                self._show_msg('提示', '请手动输入坐标')
                return
            device = self._get_device()
            try:
                png_data = adb_screencap(device)
                ss_path = os.path.join(self.user_data_dir, 'screenshot.png')
                with open(ss_path, 'wb') as f:
                    f.write(png_data)
                size = get_screen_size(device)
                self.coord_label.text = f'屏幕: {size[0]}x{size[1]}'
                self.pos_label.text = '截图已保存，请输入坐标'
            except Exception as e:
                self._show_msg('错误', f'截图失败: {e}')

        # 手动输入坐标
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
        btn_row.add_widget(Button(text='截图', on_press=capture,
                                  background_color=self._hex('#1565C0'),
                                  color=(1, 1, 1, 1)))
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
            op, p1, p2 = card.get_params()
            if op == 0:
                ops.append(f'cl({p1},{p2})')
            elif op == 1:
                ops.append(f'dc({p1},{p2})')
            elif op == 2:
                ops.append(f'rc({p1},{p2})')
            elif op == 3:
                ops.append(f'mv({p1},{p2})')
            elif op == 4:
                ops.append(f'pd({p1},{p2})')
            elif op == 5:
                ops.append('rl()')
            elif op == 6:
                ops.append(f'dl({p1})')

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
            params = part[3:-1]
            op = CMD_MAP.get(cmd)
            if op is None:
                continue
            val1 = val2 = None
            if cmd in ('cl', 'dc', 'rc', 'mv', 'pd') and params:
                parts_xy = params.split(',')
                val1 = int(parts_xy[0].strip())
                val2 = int(parts_xy[1].strip())
            elif cmd == 'dl' and params:
                val1 = float(params.strip())
            self.add_card(op, val1, val2)

    # ─────────── 弹出消息 ───────────

    def _show_msg(self, title, msg):
        popup = Popup(title=title,
                      content=Label(text=msg, text_size=(dp(250), None)),
                      size_hint=(0.7, 0.3))
        popup.open()


# ─────────────────── 入口 ───────────────────
if __name__ == '__main__':
    NekoClickApp().run()
