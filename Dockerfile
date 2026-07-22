FROM public.ecr.aws/lts/ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# 系统依赖
RUN apt update && apt install -y \
    git zip unzip openjdk-17-jdk python3-pip autoconf \
    libtool pkg-config zlib1g-dev libncurses5-dev \
    libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev \
    python3-venv ccache sudo curl && \
    apt clean

# 强制 Python 全局跳过 SSL 证书验证（解决 Docker Desktop urllib SSL 兼容性问题）
RUN mkdir -p /root/.local/lib/python3.10/site-packages && \
    printf '%s\n' 'import ssl, os' 'if os.environ.get("PYTHONHTTPSVERIFY", "0") == "0":' '    ssl._create_default_https_context = ssl._create_unverified_context' > /root/.local/lib/python3.10/site-packages/sitecustomize.py && \
    git config --global http.sslVerify false && \
    pip3 install --user buildozer && \
    python3 -c "p='/root/.local/lib/python3.10/site-packages/buildozer/__init__.py';c=open(p).read();c=c.replace('def check_root(self):','def check_root(self):\n        return');open(p,'w').write(c)"

ENV PATH="/root/.local/bin:${PATH}"
ENV PYTHONHTTPSVERIFY=0

WORKDIR /app
COPY . .

CMD ["buildozer", "android", "debug"]
