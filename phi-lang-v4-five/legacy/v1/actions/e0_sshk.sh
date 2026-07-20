#!/bin/bash
# e0_sshk.sh — Share SSH key
cat ~/.ssh/id_ed25519.pub 2>/dev/null && echo "φsshk:pk_sent" || echo "φerr:reason=no_ssh_key"
