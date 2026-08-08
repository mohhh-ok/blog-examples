FROM mcr.microsoft.com/devcontainers/typescript-node:22

# Dependencies of init-firewall.sh:
#   iptables / iptables-save -> iptables
#   ipset                    -> ipset
#   ip (route)               -> iproute2
#   dig                      -> dnsutils
#   aggregate                -> aggregate
#   jq                       -> jq
#   curl                     -> curl
RUN apt-get update && apt-get install -y --no-install-recommends \
  iptables \
  ipset \
  iproute2 \
  dnsutils \
  aggregate \
  jq \
  curl \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy and set up firewall script; allow the node user to run it via
# passwordless sudo (same approach as the official reference Dockerfile:
# https://github.com/anthropics/claude-code/blob/main/.devcontainer/Dockerfile)
# NOTE: the claude-code feature overwrites this path with its own copy at a
# later build stage; postStartCommand copies the patched version back.
COPY init-firewall.sh /usr/local/bin/init-firewall.sh
RUN chmod +x /usr/local/bin/init-firewall.sh && \
  echo "node ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh" > /etc/sudoers.d/node-firewall && \
  chmod 0440 /etc/sudoers.d/node-firewall
