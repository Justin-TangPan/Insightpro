FROM nousresearch/hermes-agent:v2026.8.19@sha256:3811ed13da874fba2ac99b6d492db9a203d34cb6dccf90d886948c00d0ccec09

COPY services/insight-agent/plugins/sac/requirements-test.txt /tmp/sac-requirements.txt
ARG TARGETARCH=amd64
RUN case "$TARGETARCH" in amd64) terraform_sha=71fc43d92ea09907be5d416d2405a6a9c2d1ceaed633f5e175c0af26e8c4b365 ;; arm64) terraform_sha=fa82fb1b08354573467557f33e6a15e7f9e1bba74eb15492f151ca27525d2acc ;; *) exit 1 ;; esac \
    && curl -fsSL -o /tmp/terraform.zip https://releases.hashicorp.com/terraform/1.13.3/terraform_1.13.3_linux_${TARGETARCH}.zip \
    && echo "$terraform_sha  /tmp/terraform.zip" | sha256sum -c - \
    && python -m zipfile -e /tmp/terraform.zip /tmp/terraform \
    && install -m 0555 /tmp/terraform/terraform /usr/local/bin/terraform \
    && uv pip install --python /opt/hermes/.venv/bin/python -r /tmp/sac-requirements.txt \
    && rm -f /tmp/sac-requirements.txt \
    && rm -rf /tmp/terraform /tmp/terraform.zip

COPY deploy/hermes/runtime-manager.mjs deploy/hermes/AGENTS.override.md /opt/insight-agent/
COPY services/insight-agent/plugins/ /opt/insight-agent/plugins/
RUN chmod 0555 /opt/insight-agent/runtime-manager.mjs \
    && chmod 0444 /opt/insight-agent/AGENTS.override.md \
    && chmod -R a=rX /opt/insight-agent/plugins

ENV HERMES_HOME=/opt/data \
    HERMES_WRITE_SAFE_ROOT=/workspace \
    HERMES_DISABLE_LAZY_INSTALLS=1

WORKDIR /srv/insight-agent
ENTRYPOINT ["node", "/opt/insight-agent/runtime-manager.mjs"]
