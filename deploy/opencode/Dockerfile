FROM node:22-bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      bash \
      build-essential \
      ca-certificates \
      curl \
      git \
      python3 \
      python3-pip \
      python3-venv \
      tini \
    && npm install --global opencode-ai@1.18.23 \
    && chmod -R a+rX /usr/local/lib/node_modules/opencode-ai \
    && groupadd --gid 10002 opencode \
    && useradd --uid 10002 --gid opencode --create-home opencode \
    && install -d -o opencode -g opencode \
      /home/opencode/.cache \
      /home/opencode/.config/opencode \
      /home/opencode/.local/share/opencode \
      /home/opencode/.local/state/opencode \
      /workspace \
    && rm -rf /var/lib/apt/lists/*

ENV HOME=/home/opencode \
    XDG_CACHE_HOME=/home/opencode/.cache \
    XDG_CONFIG_HOME=/home/opencode/.config \
    XDG_DATA_HOME=/home/opencode/.local/share \
    XDG_STATE_HOME=/home/opencode/.local/state \
    NPM_CONFIG_CACHE=/home/opencode/.cache/npm \
    PIP_NO_CACHE_DIR=1

WORKDIR /workspace
USER opencode

ENTRYPOINT ["/usr/bin/tini", "--", "opencode"]
