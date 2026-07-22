# NekoClick Mobile — 安卓自动点击器

基于 Kivy 的移动版，通过 ADB 模拟点击操作。

---

## 构建 APK（三种方式）

### 方式一：Docker（推荐，最省心）

需要安装 [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)。

```bash
cd AutoClick_mobile

# 构建 Docker 镜像
docker build -t nekoclick-builder .

# 运行构建（SDK/NDK 会缓存到本地卷）
docker run --rm -v %cd%:/app -v buildozer-cache:/root/.buildozer nekoclick-builder

# APK 生成在 dist/ 目录
```

### 方式二：GitHub Actions（在线构建，无需本地环境）

1. 把本项目推到 GitHub 仓库
2. 进入仓库 Actions 页面
3. 选择 **Build APK** 工作流，点击 **Run workflow**
4. 等待约 30 分钟，APK 自动生成在 Artifacts 中

### 方式三：WSL2 + Buildozer（传统方式）

```bash
# 在 WSL Ubuntu 中
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf \
    libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev \
    libtinfo5 cmake libffi-dev libssl-dev python3-venv ccache

pip3 install --user buildozer
export PATH=$PATH:~/.local/bin

cd /mnt/d/Tools/Reasonix/global-workspace/AutoClick_mobile
buildozer android debug
```

---

## 安装到手机

1. 开启手机 **开发者选项** → **USB 调试**
2. 连接电脑，确认 `adb devices` 可识别
3. 安装：
   ```bash
   adb install dist/NekoClick-*.apk
   ```

## 使用说明

启动 App，将手机通过 USB 连接电脑并开启 ADB 调试。

| 按钮 | 功能 |
|------|------|
| 🎯 定位 | 截图 + 输入坐标，填入最后一组 |
| ▶ 执行 | 按顺序执行所有操作 |
| 💾 保存 | 保存计划为 .txt 文件 |
| 📂 打开 | 加载 .txt 计划文件 |
| 🔁 重复 | 设置重复次数并批量执行 |
| 🗑 清空 | 清空所有操作 |

### 操作类型

- **单击 / 双击 / 右键 / 移动 / 按下** → 需 X, Y 坐标
- **释放** → 无参数
- **延迟** → 需等待秒数

---

## 项目文件

```
AutoClick_mobile/
├── main.py                          # Kivy 主程序
├── buildozer.spec                   # Buildozer 构建配置
├── Dockerfile                       # Docker 构建
├── nekoclick_icon.png               # App 图标
├── requirements.txt                 # Python 依赖
├── README.md                        # 本文件
└── .github/workflows/build-apk.yml  # GitHub Actions CI
```
