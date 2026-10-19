FROM node:22.22.0-bookworm-slim@sha256:dd9d21971ec4395903fa6143c2b9267d048ae01ca6d3ea96f16cb30df6187d94
RUN apt-get update && apt-get install -y --no-install-recommends python3 git curl ca-certificates && rm -rf /var/lib/apt/lists/*
# Inspect SWE 0.2.71 detects this installation; avoid its floating npm resolver.
RUN mkdir -p /var/tmp/.5c95f967ca830048/codex-acp && cd /var/tmp/.5c95f967ca830048/codex-acp && npm install --save-exact @zed-industries/codex-acp@0.16.0
RUN mkdir -p /workspace /home/user
WORKDIR /workspace
CMD ["sleep", "infinity"]
