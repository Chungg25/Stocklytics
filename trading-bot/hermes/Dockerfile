# Hermes Agent image with the Stocklytics trading skill baked in.
# Pin HERMES_VERSION to a tested release tag (or a digest) in production.
ARG HERMES_VERSION=stable
FROM nousresearch/hermes-agent:${HERMES_VERSION}

COPY skills/ /opt/stocklytics/skills/
