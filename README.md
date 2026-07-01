# Change IP

A macOS desktop application built with Python and Kivy that displays your current public IP address and lets you trigger an IP change via a configurable endpoint.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Kivy](https://img.shields.io/badge/Kivy-2.3-green)
![macOS](https://img.shields.io/badge/macOS-native-orange)

## Features

- **Show current IP** — fetches your public IP from [ifconfig.me](https://ifconfig.me) on launch
- **Change IP** — sends a request to a configurable URL (e.g. a VPN or proxy trigger endpoint), then re-checks the IP
- **IP change detection** — compares old vs new IP and shows:
  - 🔵 Blue — initial state
  - 🟢 Green — IP changed successfully
  - 🔴 Red — IP was not changed
  - 🟡 Yellow — warnings (e.g. no URL configured)
- **Refresh** — manually re-fetch the current IP at any time
- Modern dark UI with rounded cards and clear typography

## Requirements

- macOS (tested on Apple Silicon)
- Python 3.12–3.13
- [uv](https://docs.astral.sh/uv/) package manager

## Quick start

```sh
# Clone the repo
git clone <your-repo-url>
cd change-ip

# Install uv (if you don't have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python and dependencies
uv python install 3.13
uv sync

# Run the app
uv run python app.py
```

## Configuration

All configuration is done via environment variables:

| Variable | Default | Description |
|---|---|---|
| `IP_CHECK_URL` | `https://ifconfig.me/ip` | URL to fetch the current public IP from |
| `CHANGE_IP_URL` | *(empty)* | URL to call when "Change IP" is pressed |

### Examples

```sh
# Use a different IP check service
export IP_CHECK_URL="https://api.ipify.org"

# Point to your VPN/proxy trigger endpoint
export CHANGE_IP_URL="https://your-service.example.com/change"

# Run with custom config
uv run python app.py
```

### How it works

1. On launch the app fetches your public IP from `IP_CHECK_URL`
2. Press **CHANGE IP** to call `CHANGE_IP_URL` (your VPN/proxy trigger)
3. After 2 seconds the app re-fetches the IP and compares it to the previous one
4. The result is displayed with color-coded feedback

## Running on another Mac

```sh
# 1. Make sure uv is installed
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env

# 2. Clone and enter the project
git clone <your-repo-url>
cd change-ip

# 3. Install Python 3.13 and project dependencies
uv python install 3.13
uv sync

# 4. (Optional) Set your change endpoint
export CHANGE_IP_URL="https://your-service.example.com/change"

# 5. Run
uv run python app.py
```

> **Note:** The first run may take a few seconds as uv downloads and installs dependencies into a local virtual environment. Subsequent runs are instant.

## Project structure

```
change-ip/
├── app.py            # Main application (Kivy GUI + IP logic)
├── pyproject.toml    # Project metadata and dependencies
├── uv.lock           # Locked dependency versions
├── .python-version   # Pinned Python version (3.13)
└── README.md
```

## License

MIT
