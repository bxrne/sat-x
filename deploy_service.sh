#!/bin/bash

# Configuration
SERVICE_NAME="sat-x"
SERVICE_FILE="${SERVICE_NAME}.service"
PROJECT_DIR="/home/bxrne/sat-x"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
SOURCE_SERVICE_PATH="${PROJECT_DIR}/${SERVICE_FILE}"
TARGET_SERVICE_PATH="${SYSTEMD_USER_DIR}/${SERVICE_FILE}"

echo "Deploying ${SERVICE_NAME} systemd user service..."

# Check if the source service file exists
if [ ! -f "${SOURCE_SERVICE_PATH}" ]; then
    echo "ERROR: Service file not found at ${SOURCE_SERVICE_PATH}"
    exit 1
fi

# Ensure the target directory exists
mkdir -p "${SYSTEMD_USER_DIR}"
echo "Ensured systemd user directory exists: ${SYSTEMD_USER_DIR}"

# Copy the service file
echo "Copying ${SOURCE_SERVICE_PATH} to ${TARGET_SERVICE_PATH}..."
cp "${SOURCE_SERVICE_PATH}" "${TARGET_SERVICE_PATH}"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to copy service file."
    exit 1
fi

# Reload systemd user daemon
echo "Reloading systemd user daemon..."
systemctl --user daemon-reload
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to reload systemd user daemon."
    # Attempt to clean up copied file
    rm "${TARGET_SERVICE_PATH}"
    exit 1
fi

# Enable and start the service
echo "Enabling and starting ${SERVICE_NAME} service..."
systemctl --user enable --now "${SERVICE_NAME}.service"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to enable or start the service."
    echo "Check service status with: systemctl --user status ${SERVICE_NAME}.service"
    echo "Check service logs with: journalctl --user -u ${SERVICE_NAME}.service"
    exit 1
fi

echo "Service ${SERVICE_NAME} deployed and started successfully."
echo "You can check the status with: systemctl --user status ${SERVICE_NAME}.service"
echo "You can view logs with: journalctl --user -u ${SERVICE_NAME}.service"
echo "To stop the service: systemctl --user stop ${SERVICE_NAME}.service"
echo "To disable the service from starting on boot: systemctl --user disable ${SERVICE_NAME}.service"

exit 0
