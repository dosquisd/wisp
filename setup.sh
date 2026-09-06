#!/bin/bash

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

WISP_GROUP="wisp"
WISP_INSTALL_DIR="/usr/local/lib/wisp"
SOCKET_PATH="/run/wisp.sock"
PULUMI_INSTALL_DIR="/usr/local/lib/wisp/pulumi"
SKIP_PULUMI=false

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/" && pwd)"

source ${PROJECT_ROOT}/scripts/utils.sh

function ensureCurl() {
    if command -v curl &>/dev/null; then
        return
    fi

    echo -e "${GREEN}Instalando curl...${NC}"
    case "${OS}" in
        ubuntu|debian) installPackages apt-get install -y curl ;;
        fedora) installPackages dnf install -y curl ;;
        centos|almalinux|rocky) installPackages yum install -y curl ;;
        oracle) installPackages dnf install -y curl ;;
        arch) installPackages pacman -S --needed --noconfirm curl ;;
        alpine) installPackages apk add curl ;;
    esac
}

function installPulumi() {
    if command -v pulumi &>/dev/null; then
        echo -e "${GREEN}Pulumi is already installed. Skipping.${NC}"
        return
    fi

    if ! command -v curl &>/dev/null; then
        echo -e "${RED}curl is neccesary to install Pulumi but it is not available.${NC}"
        exit 1
    fi

    echo -e "${GREEN}Installing Pulumi in ${PULUMI_INSTALL_DIR}...${NC}"
    curl -fsSL https://get.pulumi.com | sh -s -- --install-root "${PULUMI_INSTALL_DIR}" --no-edit-path

    ln -sf "${PULUMI_INSTALL_DIR}/bin/pulumi" /usr/local/bin/pulumi

    echo -e "${GREEN}Pulumi installaed and linked in /usr/local/bin/pulumi${NC}"
}

function createWispGroup() {
    echo -e "${GREEN}Creating group '${WISP_GROUP}'...${NC}"
    if ! getent group "${WISP_GROUP}" >/dev/null; then
        groupadd "${WISP_GROUP}"
        echo -e "${GREEN}Group '${WISP_GROUP}' created.${NC}"
    fi

    if [[ -n "${SUDO_USER:-}" ]]; then
        usermod -aG "${WISP_GROUP}" "${SUDO_USER}"
        echo -e "${GREEN}User '${SUDO_USER}' added to group '${WISP_GROUP}'.${NC}"
        echo "Close your session and log back in (or run 'newgrp ${WISP_GROUP}') for the change to take effect."
    else
        echo -e "${RED}No SUDO_USER detected. Add your user manually:${NC}"
        echo "  sudo usermod -aG ${WISP_GROUP} <user>"
    fi
}

function installDaemonFiles() {
    mkdir -p "${WISP_INSTALL_DIR}"

    # Copy the source code to the installation directory
    cp -r "${PROJECT_ROOT}/src" "${WISP_INSTALL_DIR}/src"

    # Create a virtual environment for the daemon, isolated from the user's development environment
    python3 -m venv "${WISP_INSTALL_DIR}/venv"
    "${WISP_INSTALL_DIR}/venv/bin/pip" install --quiet --upgrade pip
    # Install only the dependencies needed for the daemon (probably nothing external)

    echo -e "${GREEN}Daemon files installed in ${WISP_INSTALL_DIR}${NC}"
}

function installSystemdUnits() {
    cp "${PROJECT_ROOT}/packaging/wisp.socket" /etc/systemd/system/wisp.socket
    cp "${PROJECT_ROOT}/packaging/wisp.service" /etc/systemd/system/wisp.service

    systemctl daemon-reload
    systemctl enable --now wisp.socket

    echo -e "${GREEN}Socket and service installed and enabled.${NC}"
}

function initialCheck() {
    isRoot
    checkOS
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-pulumi)
            SKIP_PULUMI=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown argument: $1${NC}"
            exit 1
            ;;
    esac
done

initialCheck
ensureCurl
installWireGuardClient
[[ "${SKIP_PULUMI}" == false ]] && installPulumi
createWispGroup
installDaemonFiles
installSystemdUnits

echo ""
echo -e "${GREEN}Ready. Remember to log out and log back in to use wisp without sudo.${NC}"
