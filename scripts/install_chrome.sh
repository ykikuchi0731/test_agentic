#!/bin/bash
# Install Chrome and ChromeDriver for browser automation
# This script installs Google Chrome and required dependencies for Selenium

set -e

echo "=========================================="
echo "Installing Google Chrome for Selenium"
echo "=========================================="
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

echo "Step 1: Updating package lists..."
apt-get update

echo
echo "Step 2: Installing dependencies..."
apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    apt-transport-https \
    software-properties-common \
    unzip \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libgbm1

echo
echo "Step 3: Adding Google Chrome repository..."
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

echo
echo "Step 4: Installing Google Chrome..."
apt-get update
apt-get install -y google-chrome-stable

echo
echo "Step 5: Verifying installation..."
google-chrome --version

echo
echo "=========================================="
echo "✅ Installation complete!"
echo "=========================================="
echo
echo "Chrome version:"
google-chrome --version
echo
echo "ChromeDriver will be automatically downloaded by webdriver-manager"
echo "when you run the export script."
echo
echo "To test the installation, run:"
echo "  python -m examples.export_google_doc_browser"
echo
