
# Antigravity: Modules

This document provides context for the modules within the Waveshare E-Paper Dashboard project for the Antigravity AI assistant.

## Overview

This directory contains the core logic modules of the application, responsible for collecting and processing data.

## Key Modules

-   `weather.py`: Fetches, processes, and provides weather data. See `README_weather.md` for more details.
-   `google_calendar.py`: Manages all interaction with the Google Calendar API, including authorization and event fetching. See `README_google_calendar.md` for more details.
-   `time.py`: A simple module for fetching and formatting the current time and date from the system clock.
-   `display.py`: The main rendering module that assembles the image from individual panels and sends it to the e-ink display.
-   `layout.py`: Loads and parses the `layout.yaml` file, which defines the layout of the panels on the screen.
-   `drawing_utils.py`: A set of helper functions for drawing, loading fonts, and rendering SVG icons.
-   `panels/`: This subdirectory contains modules responsible for drawing specific sections (panels) on the screen. See the `GEMINI.md` file in that directory for more information.
