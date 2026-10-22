FROM debian:trixie-slim
RUN apt-get update && apt-get install -y --no-install-recommends squashfs-tools zsync file desktop-file-utils ca-certificates \
    && rm -rf /var/lib/apt/lists/*
