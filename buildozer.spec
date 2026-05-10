[app]
title = 拉码器
package.name = lamaqi
package.domain = org.sniffconverter
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt,json
version = 3.1.0

requirements = python3,kivy==2.2.0,qrcode[pil],pillow

orientation = portrait
screenorientation = portrait

android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE

# 图标配置
android.icon_filename = icon.png
android.presplash_filename = presplash.png

# 构建相关配置
android.archs = arm64-v8a, armeabi-v7a
fullscreen = 0
