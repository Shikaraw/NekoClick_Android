[app]

# 应用信息
title = NekoClick
package.name = nekoclick
package.domain = org.nekoclick
version = 1.0.0
version.revision = 1

# 源代码
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt
source.exclude_dirs = tests
source.exclude_exts = spec

# 构建参数
requirements = python3,kivy@master
presplash.color = #F5F5F5

# 图标
icon.filename = nekoclick_icon.png

# 权限
android.permissions = INTERNET,VIBRATE
android.api = 34
android.minapi = 21
android.ndk = 28c
android.accept_sdk_license = True

# 方向
orientation = landscape

# 全屏
fullscreen = 0

# 应用日志
android.logcat_filters = *:S python:D

# 调试模式（首次打包用 1 方便看错误）
android.debug = 1

[buildozer]

log_level = 2
warn_on_root = 1
# 归档目录
export_dir = ./dist
