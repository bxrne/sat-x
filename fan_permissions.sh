#!/bin/bash

# Setup script for sat-x fan control permissions
# This script installs udev rules and sets up proper permissions for fan control

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UDEV_RULES_FILE="99-sat-x-fan-control.rules"
UDEV_RULES_SOURCE="${SCRIPT_DIR}/${UDEV_RULES_FILE}"
UDEV_RULES_TARGET="/etc/udev/rules.d/${UDEV_RULES_FILE}"

echo "Setting up sat-x fan control permissions..."

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "This script needs to be run with sudo to install udev rules."
    echo "Usage: sudo $0"
    exit 1
fi

# Check if the udev rules file exists
if [ ! -f "${UDEV_RULES_SOURCE}" ]; then
    echo "ERROR: udev rules file not found at ${UDEV_RULES_SOURCE}"
    exit 1
fi

# Install the udev rules
echo "Installing udev rules..."
cp "${UDEV_RULES_SOURCE}" "${UDEV_RULES_TARGET}"
echo "Installed ${UDEV_RULES_FILE} to ${UDEV_RULES_TARGET}"

# Set correct permissions on the rules file
chmod 644 "${UDEV_RULES_TARGET}"
chown root:root "${UDEV_RULES_TARGET}"

# Reload udev rules
echo "Reloading udev rules..."
udevadm control --reload-rules
udevadm trigger

# Apply permissions immediately to existing devices
echo "Applying permissions to existing fan control devices..."
FAN_PWM_PATH="/sys/devices/platform/cooling_fan/hwmon/hwmon2/pwm1"
FAN_ENABLE_PATH="/sys/devices/platform/cooling_fan/hwmon/hwmon2/pwm1_enable"

if [ -e "${FAN_PWM_PATH}" ]; then
    chgrp gpio "${FAN_PWM_PATH}"
    chmod 664 "${FAN_PWM_PATH}"
    echo "Set permissions on ${FAN_PWM_PATH}"
else
    echo "WARNING: ${FAN_PWM_PATH} not found"
fi

if [ -e "${FAN_ENABLE_PATH}" ]; then
    chgrp gpio "${FAN_ENABLE_PATH}"
    chmod 664 "${FAN_ENABLE_PATH}"
    echo "Set permissions on ${FAN_ENABLE_PATH}"
else
    echo "WARNING: ${FAN_ENABLE_PATH} not found"
fi

# Verify the user is in the gpio group
CURRENT_USER="${SUDO_USER:-$(logname)}"
if groups "${CURRENT_USER}" | grep -q "\bgpio\b"; then
    echo "User ${CURRENT_USER} is in the gpio group - good!"
else
    echo "WARNING: User ${CURRENT_USER} is not in the gpio group."
    echo "Add user to gpio group with: sudo usermod -a -G gpio ${CURRENT_USER}"
    echo "Then log out and log back in for the group change to take effect."
fi

echo "Fan control permissions setup completed!"
echo ""
echo "To test the setup:"
echo "1. Check permissions: ls -la ${FAN_PWM_PATH}"
echo "2. Test write access: echo 100 > ${FAN_PWM_PATH}"
echo "3. Restart the sat-x service: systemctl --user restart sat-x" 