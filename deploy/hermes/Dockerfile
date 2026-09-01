FROM nousresearch/hermes-agent:v2026.8.19@sha256:3811ed13da874fba2ac99b6d492db9a203d34cb6dccf90d886948c00d0ccec09

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
