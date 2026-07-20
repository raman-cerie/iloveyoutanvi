#!/bin/bash
# c4_deploy.sh — Deploy update from GitHub repo (Tier 2 — needs binary gate approval first)
cd ~/installations/language && git pull 2>&1 && echo "φack:id=deploy,status=pulled,v=$(git rev-parse --short HEAD)"

