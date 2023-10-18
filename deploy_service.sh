#!/bin/sh

set -e

# Get the current username and directory
if [ -n "$SUDO_USER" ]; then
    current_user=$SUDO_USER
else
    current_user=$(whoami)
fi
current_dir=$(pwd)

# Create a temporary service file by replacing placeholders
sed "s/__USER__/$current_user/g; s|__DIR__|$current_dir|g" figma_ui.template.service > figma_ui.service

# Copy the systemd service file to the systemd folder
sudo cp figma_ui.service /etc/systemd/system/

# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable and start the service
sudo systemctl enable figma_ui
sudo systemctl start figma_ui

echo "Service deployed for user: $current_user, directory: $current_dir"
