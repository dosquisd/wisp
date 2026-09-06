#!/bin/bash

# Licensed under MIT License
# Copyright (c) 2019 angristan

RED='\033[0;31m'
ORANGE='\033[0;33m'
GREEN='\033[0;32m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

source ${PROJECT_ROOT}/scripts/utils.sh

function initialCheck() {
    isRoot
    checkOS
}

initialCheck

if [[ ${1} == "uninstall" ]]; then
    uninstallWg
else
    installWireGuardClient
fi
