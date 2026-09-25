# Ghost-Desktop: Ephemeral Sandboxed Container Environment
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99
ENV RESOLUTION=1280x800x24

RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    x11vnc \
    openbox \
    xdotool \
    scrot \
    novnc \
    websockify \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN python3 -m pip install --break-system-packages pillow

EXPOSE 8787 5900 6080

CMD ["python3", "-m", "ghost_desktop.cli", "demo"]
