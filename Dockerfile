FROM alpine:3.20 AS tex
RUN apk add --no-cache curl && \
    cd /tmp && curl -fsSL https://drop-sh.fullyjustified.net | sh && \
    mkdir -p /out/jobs /out/tectonic-cache && mv tectonic /out/tectonic

FROM n8nio/n8n:2.42.4
COPY --from=tex /out/tectonic /usr/local/bin/tectonic
COPY --from=tex --chown=1000:1000 /out/jobs /data/jobs
COPY --from=tex --chown=1000:1000 /out/tectonic-cache /data/tectonic-cache
