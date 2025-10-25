#!/bin/bash
# Hailo AI HAT+ Setup Script for Shifusenpi-Bot
# This script installs and configures Hailo integration

set -e  # Exit on error

echo "=============================================="
echo " Hailo AI HAT+ Integration Setup"
echo " for Shifusenpi-Bot"
echo "=============================================="
echo

# Check if running on Raspberry Pi 5
echo "[1/7] Checking system compatibility..."
if [ ! -f /proc/device-tree/model ]; then
    echo "WARNING: Cannot detect Raspberry Pi model"
else
    MODEL=$(cat /proc/device-tree/model)
    echo "Detected: $MODEL"
    if [[ ! "$MODEL" =~ "Raspberry Pi 5" ]]; then
        echo "WARNING: This script is designed for Raspberry Pi 5"
        read -p "Continue anyway? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# Check for Hailo hardware
echo
echo "[2/7] Checking for Hailo AI HAT+..."
if lspci | grep -q "Hailo"; then
    echo "✓ Hailo device detected:"
    lspci | grep "Hailo"
else
    echo "⚠ Hailo device NOT detected"
    echo "Please ensure Hailo AI HAT+ is properly connected"
    read -p "Continue anyway (for testing)? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if hailo-rpi5-examples exists
echo
echo "[3/7] Checking for Hailo examples repository..."
HAILO_DIR="$HOME/hailo-rpi5-examples"
if [ ! -d "$HAILO_DIR" ]; then
    echo "Hailo examples not found. Cloning repository..."
    cd $HOME
    git clone https://github.com/hailo-ai/hailo-rpi5-examples.git
    cd hailo-rpi5-examples
else
    echo "✓ Hailo examples found at $HAILO_DIR"
    cd "$HAILO_DIR"
fi

# Install Hailo software
echo
echo "[4/7] Installing Hailo software stack..."
if [ ! -f "$HAILO_DIR/setup_env.sh" ]; then
    echo "Running Hailo install script..."
    ./install.sh
else
    echo "Hailo already installed, sourcing environment..."
    source setup_env.sh
fi

# Download Hailo models
echo
echo "[5/7] Downloading Hailo models..."
if [ -d "$HAILO_DIR/resources/models" ] && [ "$(ls -A $HAILO_DIR/resources/models/*.hef 2>/dev/null)" ]; then
    echo "✓ Models already downloaded"
else
    echo "Downloading models..."
    ./download_resources.sh --all
fi

# Install Python dependencies for integration
echo
echo "[6/7] Installing integration dependencies..."
cd ~/shifusenpi-bot
pip3 install -r requirements_hailo.txt || true  # Don't fail if some packages not available

# Link Hailo resources
echo
echo "[7/7] Creating symbolic links..."
if [ ! -L ~/shifusenpi-bot/hailo_resources ]; then
    ln -s "$HAILO_DIR/resources" ~/shifusenpi-bot/hailo_resources
    echo "✓ Linked Hailo resources"
else
    echo "✓ Hailo resources already linked"
fi

# Create models directory
mkdir -p ~/shifusenpi-bot/models
echo "✓ Created models directory"

# Summary
echo
echo "=============================================="
echo " Installation Complete!"
echo "=============================================="
echo
echo "Next steps:"
echo "1. Test Hailo hardware:"
echo "   cd ~/hailo-rpi5-examples"
echo "   source setup_env.sh"
echo "   python basic_pipelines/detection_simple.py --input rpi"
echo
echo "2. Test vision integration:"
echo "   cd ~/shifusenpi-bot"
echo "   python src/test_vision_integration.py"
echo
echo "3. Read integration documentation:"
echo "   cat docs/HAILO_INTEGRATION_PLAN.md"
echo
echo "=============================================="
echo "Setup complete! Enjoy your AI-powered robot!"
echo "=============================================="
