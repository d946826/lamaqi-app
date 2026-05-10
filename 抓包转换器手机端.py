#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拉码器 - 手机端APP
功能：抓包识别支付链接，发送到电脑，生成二维码
连接服务器后台进行用户认证
"""

import kivy
kivy.require('2.1.0')

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.checkbox import CheckBox
from kivy.uix.popup import Popup
from kivy.uix.image import Image as KvImage
from kivy.uix.spinner import Spinner
from kivy.uix.switch import Switch
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.storage.jsonstore import JsonStore
from kivy.core.window import Window
from kivy.base import EventLoop
import socket
import json
import threading
import time
import io
import qrcode
import base64
import ssl
import struct
import os
import urllib.request
import urllib.error

# ============== 配置 ==============
# 服务器后台地址 - 修改为你的服务器IP
SERVER_HOST = "121.41.191.1"
SERVER_PORT = 5000
SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

DEFAULT_SERVER_IP = ""  # 电脑IP地址，需要用户设置
DEFAULT_SERVER_PORT = 8888

# 版本号 - 从服务器自动获取
CLIENT_VERSION = "1.0.0"  # 默认版本

def get_server_version():
    """从服务器获取版本号"""
    global CLIENT_VERSION
    try:
        url = f"{SERVER_URL}/api/version"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get("success"):
                CLIENT_VERSION = result.get("version")
    except:
        pass
    return CLIENT_VERSION

# 平台配置
PLATFORMS = {
    "京东": ["*.jd.com", "*.jd.hk", "*.jdpay.com", "*.jding.me"],
    "拼多多": ["*.pinduoduo.com", "*.yangkeduo.com", "*.pddapi.com"],
    "淘宝": ["*.taobao.com", "*.tmall.com", "*.alibaba.com", "*.1688.com"],
    "闲鱼": ["*.guazi.com", "*.2tao.com", "*.xianyu.com"],
    "小红书": ["*.xiaohongshu.com", "*.xhscdn.com"],
    "抖音": ["*.douyin.com", "*.toutiao.com", "*.bytedance.com", "*.snssdk.com"]
}

# ============== 全局变量 ==============
store = None
connected = False
sniffing = False
current_platforms = []
captured_urls = []
current_user = None  # 当前登录用户
current_token = None  # 当前用户Token
current_settings = None  # 当前用户设置

# ============== 用户认证（连接服务器后台）==============
def verify_user(username, password):
    """验证用户登录 - 连接服务器API"""
    try:
        url = f"{SERVER_URL}/api/verify"
        payload = {
            "username": username, 
            "password": password,
            "device_type": "phone",  # 标识为手机设备
            "device_info": "手机端",
            "version": CLIENT_VERSION  # 发送版本号
        }
        data = json.dumps(payload).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if result.get("success"):
                    global current_token, current_settings, current_user
                    current_token = result.get("token")
                    current_user = username
                    current_settings = {
                        "qr_expire_time": result.get("qr_expire_time", 180),
                        "allowed_platforms": result.get("allowed_platforms", [])
                    }
                    return {
                        "success": True,
                        "user": username,
                        "token": current_token,
                        "settings": current_settings,
                        "kicked": result.get("kicked", False)
                    }
                else:
                    return {"success": False, "message": result.get("message", "认证失败")}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            try:
                error_data = json.loads(error_body)
                return {"success": False, "message": error_data.get("message", "认证失败")}
            except:
                return {"success": False, "message": f"服务器错误: {e.code}"}
        except urllib.error.URLError as e:
            return {"success": False, "message": f"无法连接服务器: {e.reason}"}
            
    except Exception as e:
        return {"success": False, "message": f"认证出错: {str(e)}"}

# ============== 登录界面 ==============
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=30, spacing=15)
        
        # 标题
        title = Label(text='[b]拉码器[/b]', markup=True, font_size='28sp', 
                     size_hint_y=0.2, halign='center')
        layout.add_widget(title)
        
        # 后台服务器信息
        server_info = Label(text=f'后台服务器: {SERVER_URL}', font_size='12sp',
                           size_hint_y=0.08, color=(0.5, 0.5, 0.5, 1))
        layout.add_widget(server_info)
        
        # 用户登录信息
        login_box = BoxLayout(orientation='vertical', spacing=10, size_hint_y=0.4)
        
        login_box.add_widget(Label(text='用户登录', font_size='16sp', 
                                    size_hint_y=0.15, halign='left'))
        
        # 用户名输入
        username_box = BoxLayout(orientation='horizontal', size_hint_y=0.2)
        username_box.add_widget(Label(text='用户名:', size_hint_x=0.3))
        self.username_input = TextInput(multiline=False, size_hint_x=0.7)
        self.username_input.text = store.get('user', {}).get('username', '')
        username_box.add_widget(self.username_input)
        login_box.add_widget(username_box)
        
        # 密码输入
        password_box = BoxLayout(orientation='horizontal', size_hint_y=0.2)
        password_box.add_widget(Label(text='密码:', size_hint_x=0.3))
        self.password_input = TextInput(multiline=False, size_hint_x=0.7, password=True)
        password_box.add_widget(self.password_input)
        login_box.add_widget(password_box)
        
        layout.add_widget(login_box)
        
        # 电脑服务器设置
        server_box = BoxLayout(orientation='vertical', spacing=10, size_hint_y=0.25)
        
        server_box.add_widget(Label(text='电脑服务器设置', font_size='14sp', 
                                    size_hint_y=0.2, halign='left'))
        
        # IP输入
        ip_box = BoxLayout(orientation='horizontal', size_hint_y=0.4)
        ip_box.add_widget(Label(text='电脑IP:', size_hint_x=0.3))
        self.ip_input = TextInput(multiline=False, size_hint_x=0.7)
        self.ip_input.text = store.get('config', {}).get('server_ip', '')
        ip_box.add_widget(self.ip_input)
        server_box.add_widget(ip_box)
        
        layout.add_widget(server_box)
        
        # 登录按钮
        login_btn = Button(text='登录并连接', size_hint_y=0.1, 
                          background_color=(0.2, 0.6, 0.8, 1),
                          on_press=self.do_login)
        layout.add_widget(login_btn)
        
        # 状态
        self.status_label = Label(text='请先登录后台账号', size_hint_y=0.07, color=(1, 0, 0, 1))
        layout.add_widget(self.status_label)
        
        self.add_widget(layout)
    
    def do_login(self, instance):
        global DEFAULT_SERVER_IP, DEFAULT_SERVER_PORT, current_user, current_token, current_settings
        
        username = self.username_input.text.strip()
        password = self.password_input.text.strip()
        ip = self.ip_input.text.strip()
        port = self.port_input.text.strip() if hasattr(self, 'port_input') else str(DEFAULT_SERVER_PORT)
        
        if not username or not password:
            self.status_label.text = '请输入用户名和密码'
            self.status_label.color = (1, 0, 0, 1)
            return
        
        if not ip:
            self.status_label.text = '请输入电脑IP地址'
            self.status_label.color = (1, 0, 0, 1)
            return
        
        try:
            port = int(port) if port else DEFAULT_SERVER_PORT
        except:
            self.status_label.text = '端口号无效'
            self.status_label.color = (1, 0, 0, 1)
            return
        
        # 保存配置
        store.put('config', server_ip=ip, server_port=port)
        store.put('user', username=username)
        
        self.status_label.text = '正在连接后台服务器...'
        self.status_label.color = (0.5, 0.5, 0, 1)
        
        # 后台认证
        threading.Thread(target=self._do_auth, args=(username, password, ip, port), daemon=True).start()
    
    def _do_auth(self, username, password, ip, port):
        """后台认证"""
        global current_user, current_token, current_settings
        
        try:
            # 验证用户
            auth_result = verify_user(username, password)
            
            if not auth_result.get("success"):
                Clock.schedule_once(lambda dt: self._on_auth_failed(auth_result.get("message", "认证失败")), 0)
                return
            
            # 保存认证信息
            current_user = auth_result.get("user")
            current_token = auth_result.get("token")
            current_settings = auth_result.get("settings", {})
            
            # 尝试连接电脑服务器
            Clock.schedule_once(lambda dt: self._on_auth_success(ip, port), 0)
            
        except Exception as e:
            Clock.schedule_once(lambda dt: self._on_auth_failed(str(e)), 0)
    
    def _on_auth_success(self, ip, port):
        self.status_label.text = f'认证成功，正在连接电脑...'
        self.status_label.color = (0, 0.8, 0, 1)
        threading.Thread(target=self._try_connect, args=(ip, port), daemon=True).start()
    
    def _on_auth_failed(self, error):
        self.status_label.text = f'认证失败: {error}'
        self.status_label.color = (1, 0, 0, 1)
    
    def _try_connect(self, ip, port):
        global connected
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((ip, port))
            sock.close()
            
            connected = True
            Clock.schedule_once(lambda dt: self._on_connected(ip, port), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._on_failed(str(e)), 0)
    
    def _on_connected(self, ip, port):
        self.status_label.text = f'已连接 {ip}:{port}'
        self.status_label.color = (0, 1, 0, 1)
        self.manager.current = 'main'
    
    def _on_failed(self, error):
        self.status_label.text = f'连接失败: {error}'
        self.status_label.color = (1, 0.5, 0, 1)

# ============== 主界面 ==============
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
        self.load_user_settings()
    
    def load_user_settings(self):
        """加载用户设置，限制可选择的平台"""
        global current_settings, PLATFORMS
        
        # 刷新版本号显示
        get_server_version()
        self.version_label.text = f'版本: {CLIENT_VERSION}'
        
        # 根据服务器返回的设置禁用未授权的平台
        if current_settings and current_settings.get("allowed_platforms"):
            allowed = current_settings["allowed_platforms"]
            for platform in PLATFORMS.keys():
                if platform in allowed:
                    self.platform_checks[platform].disabled = False
                    self.platform_checks[platform].active = False
                else:
                    self.platform_checks[platform].disabled = True
                    self.platform_checks[platform].active = False
            self.status_label.text = f'已登录: {current_user} | 平台已限制'
        else:
            # 如果没有限制，所有平台可用
            for platform in PLATFORMS.keys():
                self.platform_checks[platform].disabled = False
            self.status_label.text = f'已登录: {current_user} | 所有平台可用'
    
    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # 顶部状态栏
        top_bar = BoxLayout(orientation='horizontal', size_hint_y=0.08)
        self.status_label = Label(text='状态: 就绪', size_hint_x=0.6, halign='left')
        self.status_label.bind(size=self.status_label.setter('text_size'))
        top_bar.add_widget(self.status_label)
        
        self.platform_label = Label(text='平台: 未选择', size_hint_x=0.4)
        top_bar.add_widget(self.platform_label)
        layout.add_widget(top_bar)
        
        # 平台选择
        platform_frame = BoxLayout(orientation='vertical', size_hint_y=0.35)
        platform_frame.add_widget(Label(text='选择抓包平台', size_hint_y=0.15, halign='left'))
        
        platform_grid = GridLayout(cols=2, size_hint_y=0.85)
        self.platform_checks = {}
        
        for platform in PLATFORMS.keys():
            box = BoxLayout(orientation='horizontal', size_hint_y=0.5)
            cb = CheckBox(size_hint_x=0.2, on_press=lambda c, p=platform: self.on_platform_toggle(c, p))
            self.platform_checks[platform] = cb
            box.add_widget(cb)
            box.add_widget(Label(text=platform, size_hint_x=0.8))
            platform_grid.add_widget(box)
        
        platform_frame.add_widget(platform_grid)
        layout.add_widget(platform_frame)
        
        # 抓包控制
        control_box = BoxLayout(orientation='horizontal', size_hint_y=0.12)
        
        self.sniff_btn = Button(text='开始抓包', background_color=(0.3, 0.8, 0.3, 1),
                               on_press=self.toggle_sniff)
        self.sniff_btn.size_hint_x = 0.35
        control_box.add_widget(self.sniff_btn)
        
        pwd_btn = Button(text='改密码', background_color=(0.2, 0.5, 0.8, 1),
                        on_press=self.change_password)
        pwd_btn.size_hint_x = 0.2
        control_box.add_widget(pwd_btn)
        
        clear_btn = Button(text='清空记录', background_color=(0.8, 0.3, 0.3, 1),
                          on_press=self.clear_captures)
        clear_btn.size_hint_x = 0.2
        control_box.add_widget(clear_btn)
        
        logout_btn = Button(text='退出', background_color=(0.5, 0.5, 0.5, 1),
                           on_press=self.logout)
        logout_btn.size_hint_x = 0.25
        control_box.add_widget(logout_btn)
        
        layout.add_widget(control_box)
        
        # 二维码显示区
        qr_frame = BoxLayout(orientation='vertical', size_hint_y=0.4)
        qr_frame.add_widget(Label(text='二维码预览', size_hint_y=0.1, halign='left'))
        
        self.qr_image = Label(text='暂无数据\n\n抓取支付链接后\n将显示二维码', 
                             font_size='14sp', color=(0.5, 0.5, 0.5, 1))
        qr_frame.add_widget(self.qr_image)
        layout.add_widget(qr_frame)
        
        # 抓包记录
        history_frame = BoxLayout(orientation='vertical', size_hint_y=0.12)
        history_frame.add_widget(Label(text='最近抓取', size_hint_y=0.3, halign='left'))
        
        self.history_label = Label(text='暂无记录', size_hint_y=0.7, 
                                  color=(0.6, 0.6, 0.6, 1), halign='left')
        self.history_label.bind(size=self.history_label.setter('text_size'))
        history_frame.add_widget(self.history_label)
        layout.add_widget(history_frame)
        
        # 版本信息（底部显示）
        version_frame = BoxLayout(orientation='vertical', size_hint_y=0.03)
        self.version_label = Label(text=f'版本: {CLIENT_VERSION}', font_size='10sp', 
                                  color=(0.6, 0.6, 0.6, 1))
        version_frame.add_widget(self.version_label)
        layout.add_widget(version_frame)
        
        self.add_widget(layout)
    
    def on_platform_toggle(self, checkbox, platform):
        global current_platforms
        if checkbox.active:
            if platform not in current_platforms:
                current_platforms.append(platform)
        else:
            if platform in current_platforms:
                current_platforms.remove(platform)
        
        self.platform_label.text = f'平台: {", ".join(current_platforms) if current_platforms else "未选择"}'
    
    def toggle_sniff(self, instance):
        global sniffing
        
        if not sniffing:
            if not current_platforms:
                self.status_label.text = '请先选择抓包平台'
                self.status_label.color = (1, 0, 0, 1)
                return
            
            sniffing = True
            self.sniff_btn.text = '停止抓包'
            self.sniff_btn.background_color = (0.8, 0.3, 0.3, 1)
            self.status_label.text = '正在抓包...'
            self.status_label.color = (0, 1, 0, 1)
            
            # 启动抓包线程
            threading.Thread(target=self.start_sniffing, daemon=True).start()
        else:
            sniffing = False
            self.sniff_btn.text = '开始抓包'
            self.sniff_btn.background_color = (0.3, 0.8, 0.3, 1)
            self.status_label.text = '抓包已停止'
            self.status_label.color = (0.5, 0.5, 0.5, 1)
    
    def start_sniffing(self):
        """模拟抓包（实际使用时替换为真实抓包逻辑）"""
        # 注意：这里需要实际的抓包实现
        # 可以使用python-virtualenv或frida等工具
        pass
    
    def clear_captures(self, instance):
        global captured_urls
        captured_urls = []
        self.history_label.text = '暂无记录'
        self.status_label.text = '记录已清空'
    
    def logout(self, instance):
        global connected, sniffing, current_user, current_token, current_settings
        sniffing = False
        connected = False
        current_user = None
        current_token = None
        current_settings = None
        self.manager.current = 'login'
    
    def change_password(self, instance):
        """修改密码弹窗"""
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        content.add_widget(Label(text='修改密码', size_hint_y=0.1))
        
        content.add_widget(Label(text='当前密码:', size_hint_y=0.15, halign='left'))
        old_pwd = TextInput(multiline=False, password=True, size_hint_y=0.15)
        content.add_widget(old_pwd)
        
        content.add_widget(Label(text='新密码:', size_hint_y=0.15, halign='left'))
        new_pwd = TextInput(multiline=False, password=True, size_hint_y=0.15)
        content.add_widget(new_pwd)
        
        content.add_widget(Label(text='确认新密码:', size_hint_y=0.15, halign='left'))
        confirm_pwd = TextInput(multiline=False, password=True, size_hint_y=0.15)
        content.add_widget(confirm_pwd)
        
        self.pwd_msg_label = Label(text='', size_hint_y=0.1, color=(1, 0, 0, 1))
        content.add_widget(self.pwd_msg_label)
        
        btn_box = BoxLayout(size_hint_y=0.15)
        btn_box.add_widget(Button(text='确认', on_press=lambda x: self.do_change_password(old_pwd, new_pwd, confirm_pwd), background_color=(0.13, 0.59, 0.95, 1)))
        btn_box.add_widget(Button(text='取消', on_press=lambda x: popup.dismiss(), background_color=(0.5, 0.5, 0.5, 1)))
        content.add_widget(btn_box)
        
        popup = Popup(title='修改密码', content=content, size_hint=(0.8, 0.7), auto_dismiss=False)
        popup.open()
    
    def do_change_password(self, old_pwd, new_pwd, confirm_pwd):
        """执行修改密码"""
        old = old_pwd.text.strip()
        new = new_pwd.text.strip()
        confirm = confirm_pwd.text.strip()
        
        if not old or not new or not confirm:
            self.pwd_msg_label.text = '请填写所有字段'
            self.pwd_msg_label.color = (1, 0, 0, 1)
            return
        
        if len(new) < 6:
            self.pwd_msg_label.text = '新密码至少6位'
            self.pwd_msg_label.color = (1, 0, 0, 1)
            return
        
        if new != confirm:
            self.pwd_msg_label.text = '两次密码不一致'
            self.pwd_msg_label.color = (1, 0, 0, 1)
            return
        
        # 调用API修改密码
        try:
            url = f"{SERVER_URL}/api/change_password"
            payload = {
                "username": current_user,
                "old_password": old,
                "new_password": new
            }
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                if result.get("success"):
                    self.pwd_msg_label.text = '修改成功，请重新登录'
                    self.pwd_msg_label.color = (0, 1, 0, 1)
                    Clock.schedule_once(lambda dt: self.after_password_change(), 1.5)
                else:
                    self.pwd_msg_label.text = result.get("message", "修改失败")
                    self.pwd_msg_label.color = (1, 0, 0, 1)
        except Exception as e:
            self.pwd_msg_label.text = f'修改失败: {str(e)}'
            self.pwd_msg_label.color = (1, 0, 0, 1)
    
    def after_password_change(self):
        """修改密码后退出登录"""
        global connected, sniffing, current_user, current_token, current_settings
        sniffing = False
        connected = False
        current_user = None
        current_token = None
        current_settings = None
        self.manager.current = 'login'
    
    def show_qr(self, url):
        """显示二维码"""
        global captured_urls
        
        # 生成二维码
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L,
                          box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color='black', back_color='white')
        
        # 保存到内存
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        # 更新UI
        Clock.schedule_once(lambda dt: self._update_qr_display(img_base64, url), 0)
        
        # 添加到记录
        captured_urls.append(url)
        self.history_label.text = url[:50] + '...' if len(url) > 50 else url
    
    def _update_qr_display(self, img_base64, url):
        try:
            from kivy.core.image import Image as CoreImage
            from kivy.properties import ObjectProperty
            
            data = base64.b64decode(img_base64)
            img = CoreImage(io.BytesIO(data), ext='png').texture
            self.qr_image.text = ''
            self.qr_image.texture = img
        except Exception as e:
            self.qr_image.text = f'二维码已生成\n{url[:30]}...'
    
    def send_to_server(self, url, platform):
        """发送数据到电脑服务器"""
        global store
        
        config = store.get('config', {})
        ip = config.get('server_ip', '')
        port = config.get('server_port', DEFAULT_SERVER_PORT)
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((ip, port))
            
            data = {
                "type": "qr_data",
                "url": url,
                "platform": platform,
                "device": socket.gethostname()
            }
            
            sock.send(json.dumps(data).encode('utf-8'))
            sock.close()
            
            Clock.schedule_once(lambda dt: self.show_qr(url), 0)
            Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', '已发送到电脑'), 0)
            
        except Exception as e:
            Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', f'发送失败: {e}'), 0)

# ============== 应用主类 ==============
class SniffConverterApp(App):
    def build(self):
        global store
        # 启动时获取服务器版本号
        get_server_version()
        
        store = JsonStore('config.json')
        
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(MainScreen(name='main'))
        
        return sm
    
    def on_start(self):
        pass
    
    def on_pause(self):
        return True
    
    def on_resume(self):
        pass

if __name__ == '__main__':
    SniffConverterApp().run()
