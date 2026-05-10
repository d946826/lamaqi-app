# 手机端APK构建说明

## 方式一：使用Buildozer（推荐Linux）

### 1. 安装依赖
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.10-venv autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev

# 安装Buildozer
pip install buildozer

# 安装Android SDK
sudo apt install -y openjdk-11-jdk
```

### 2. 创建spec文件
创建 `specs/抓包转换器.spec`：
```ini
[app]
title = 抓包转换器
package.name = sniff_converter
package.domain = com.sniffconverter
source.include_exts = py,png,jpg,kv,atlas,json,ttf
version = 1.0.0

requirements = python3,kivy==2.1.0

orientation = portrait

fullscreen = 0

android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,CHANGE_WIFI_STATE
```

### 3. 构建APK
```bash
buildozer android debug
```

## 方式二：使用Kivy Launcher（测试用）

1. 安装Kivy Launcher（Google Play有）
2. 将代码放到 `sdcard/kivy/抓包转换器/` 目录
3. 在Kivy Launcher中打开即可测试

## 方式三：使用Flet（更简单）

```bash
pip install flet
flet create sniff_app
cd sniff_app
# 替换 main.py 内容
flet build apk
```

## 方式四：在线构建服务

- **CloudKivy**: https://cloud.kivy.org/
- **Konverge**: https://konverge.io/

## 抓包功能说明

APP中的抓包功能需要配合以下方式实现：

### 方案1：VPN抓包（推荐）
使用Python的 `proxy.py` 或 `mitmproxy`：
```python
# 这是一个简化版的抓包示例
# 实际需要使用Android VPN API或第三方库
```

### 方案2：HTTP代理抓包
```python
import http.server
import socketserver

class Proxy(http.server.HTTPRequestHandler):
    def do_POST(self):
        # 解析请求，识别支付链接
        pass
    
    def do_GET(self):
        # 解析URL，识别支付链接
        pass
```

### 方案3：使用第三方抓包库
```bash
pip install asyncmitm
```

## 注意事项

1. Android 10+ 需要将APK签名后才能安装
2. VPN抓包功能需要用户授权
3. HTTPS抓包需要安装根证书
4. 微信直接唤起支付无法抓包（走URL Scheme）
