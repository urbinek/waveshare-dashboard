# Antigravity: Waveshare E-Paper Dashboard

This document provides context for the Antigravity AI assistant to effectively contribute to the Waveshare E-Paper Dashboard project.

## Project Overview

The project is a personalized, grayscale (black and white with shades of gray) dashboard for a 7.5-inch Waveshare e-paper display, designed to run on a Raspberry Pi. It integrates data from various sources to create a useful and aesthetic information screen.

## Core Technologies

- **Language:** Python 3
- **Key Libraries:**
    - `waveshare_epd` for display interaction
    - `google-api-python-client` for Google Calendar integration
    - `Pillow` for image manipulation
    - `cairosvg` for SVG rendering (recommended for performance)
    - `paho-mqtt` for local Zigbee sensor data
- **Configuration:**
    - `config.yaml` for all application settings.
- **Linting:** `flake8` (configuration in `.flake8`)

## Development Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/urbinek/waveshare-dashboard
    cd waveshare-dashboard
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    # For optimal icon rendering performance, also install cairosvg
    pip install cairosvg
    ```

4.  **Configure the application:**
    - Copy `config.yaml.example` to `config.yaml` and fill in the required values (API keys, location, etc.).
    - Copy `credentials.json.example` to `credentials.json` and add your Google API credentials.

5.  **Authorize Google Calendar:**
    Run the following command and follow the on-screen instructions to authorize the application to access your Google Calendar data.
    ```bash
    python modules/google_calendar.py
    ```

## Running the Application

To run the application directly from the terminal:

```bash
source .venv/bin/activate
python main.py [ARGUMENTS]
```

### Available Arguments:

-   `--draw-borders`: Draws borders around panels for layout debugging.
-   `--service`: Optimizes log format for `systemd`.
-   `--no-splash`: Skips the splash screen.
-   `--verbose`: Enables `DEBUG` level logging.
-   `--2137`: Displays a hidden Easter Egg.
-   `--flip`: Rotates the display 180 degrees.

## Linting

To check the code for style and quality issues, run `flake8`:

```bash
flake8 .
```

The configuration for `flake8` is located in the `.flake8` file.

## Development Workflow

### Configuration Management
- **NEVER** store credentials, API keys, or any other secrets directly in Python code files (`.py`), not even in example files.
- All configuration, including API keys, **MUST** be stored in `config.yaml`.
- When you add or change a configuration setting, you **MUST** update both `config.yaml` (for your local development) and `config.yaml.example` (the template for other users).
- The `config.yaml.example` file **MUST NOT** contain any real API keys or personal information. Use placeholder values like `YOUR_API_KEY`.

### Updating Dependencies
When adding new Python packages or updating existing ones, ensure `requirements.txt` is updated accordingly. This helps maintain a consistent development environment.

## Logging Guidelines

To ensure consistent and informative logging across the project, the following guidelines are applied:

### General Principles

-   **Unified Logging:** All modules use `logging.getLogger(__name__)` for consistent log handling.
-   **Log Levels:**
    -   `DEBUG`: Highly detailed information, primarily for debugging (`--verbose` flag).
    -   `INFO`: Important application state, progress, and successful operations.
    -   `WARNING`: Potential issues that don't halt execution but might need attention.
    -   `ERROR`: Errors affecting functionality, but the application might continue.
    -   `CRITICAL`: Severe errors preventing further application operation.
-   **F-strings:** Used for clear and concise log message formatting.

### Detailed Logging (Startup/Cache Refresh)

During application startup or when cache data is stale (requiring fresh data from APIs), logging is more verbose:

-   **File Paths:** Full paths of loaded/accessed files (e.g., cache files, asset files) are logged.
-   **API Endpoints & IDs:** Full API endpoints, station IDs (for weather/air quality), and geolocation data are logged when data is fetched.
-   **Cache Operations:** Information about cache file generation, reads, and writes is logged.

### Concise Logging (Normal Operation)

Once the application is running and data is cached, logging becomes more concise:

-   **Weather Icon Changes:** An `INFO` level message is logged only if the displayed weather icon changes from the previous one.
-   **Hourly Refreshes:** `INFO` level messages indicate the start and completion of hourly full display refreshes.
-   **Minute Updates:** `DEBUG` level messages indicate the start and completion of minute-by-minute time updates (visible with `--verbose`).

### Error and Warning Visibility

-   `WARNING`, `ERROR`, and `CRITICAL` level messages are always displayed, regardless of the verbosity settings, to ensure immediate awareness of problems.

### Command-Line Flag Adaptation

-   `--service`: Optimizes log format for `systemd` (no timestamps, centered module/level names). Primarily `INFO` level and above are shown.
-   `--verbose`: Activates `DEBUG` level logging across all modules, providing maximum detail for troubleshooting. If avaliable print json reponses from API querries

## Operational Guidelines

### Git Operations
- **Commit Management:** The user prefers to manage Git commits themselves. Do not perform `git commit`, `git add`, `git push`, or similar operations unless explicitly instructed by the user. Focus on providing code modifications and summaries for the user to review and commit.
