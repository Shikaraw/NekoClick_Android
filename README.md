# NekoClick — Android 无障碍自动点击器

基于 Kivy + Android AccessibilityService 的移动版自动点击器。
**无需 ADB、无需 Root**，在手机上直接运行。

## 使用方式

1. 安装 APK
2. 打开 App → 点击「前往设置」→ 进入无障碍设置
3. 找到 **NekoClick** → 开启无障碍服务
4. 返回 App，开始添加点击操作

## 操作类型

| 按钮 | 说明 |
|------|------|
| 🎯 定位 | 手动输入坐标，填入最后一组 |
| ▶ 执行 | 按顺序执行所有操作 |
| 💾 保存 | 保存计划为 .txt 文件 |
| 📂 打开 | 加载 .txt 计划文件 |
| 🔁 重复 | 设置重复次数并批量执行 |
| 🗑 清空 | 清空所有操作 |

## 构建 APK

### GitHub Actions

1. 推送到 GitHub
2. 进入 Actions → **Build APK** → **Run workflow**
3. 等待约 30 分钟，在 Artifacts 下载 APK

### 本地 Docker

```bash
docker build -t nekoclick-builder .
docker run --rm -v %cd%:/app nekoclick-builder
```

## 技术说明

通过 Android AccessibilityService 的 `dispatchGesture` API 实现模拟点击。
需要 Android 7.0+ (API 24+)。
