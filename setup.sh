#!/bin/bash

# Update and upgrade all Ubuntu packages
sudo apt-get update
sudo apt-get upgrade -y

# Install git
sudo apt-get install git -y

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env