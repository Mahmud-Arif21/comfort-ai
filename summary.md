# ComfortAI: An Intelligent Smart Home System

## Introduction

Welcome to **ComfortAI**, your personal intelligent assistant designed to make your home smarter and more comfortable. Imagine a system that understands your needs through simple conversations, automatically adjusts your environment, and even learns your preferences over time. ComfortAI does exactly that, bringing a new level of automation and convenience to your living space.

## How it Works:

At its core, ComfortAI is like having a smart companion for your home. You interact with it through a simple chat interface, just like talking to a friend. You can tell it things like, 'It's hot in here,' or 'Turn on the light at 7 PM,' and ComfortAI understands your intent.

Behind the scenes, our system uses advanced Artificial Intelligence, capable of integrating with various Large Language Models (LLMs) via **Ollama**, to process your requests. This allows for flexible deployment on local servers. It doesn't just follow commands; it considers the current environment – like the temperature and light levels – and even learns from your past actions to make smart decisions. For example, if you often turn on the fan when it's warm, ComfortAI will start to anticipate that need.

Once ComfortAI decides on an action, whether it's turning on a fan, adjusting a light, or scheduling something for later, it sends these commands securely to your home devices using a technology called MQTT. Think of MQTT as a super-efficient messenger service for smart devices. Your devices, like an ESP32 microcontroller connected to your fan and lights, are constantly listening for these messages and react instantly.

The system also keeps track of everything: your current device settings, sensor readings, and any actions you've scheduled. It even runs continuous background tasks to ensure that scheduled actions are executed on time and that the system status is always up-to-date.

In essence, ComfortAI combines intuitive natural language interaction with intelligent automation and robust device communication, all working together to create a truly responsive and comfortable home environment tailored to you."

## Key Components (Technical Overview)

ComfortAI is structured around several interconnected modules:

1.  **User Interface (UI) (`ui.py`):**
    *   Built with Streamlit, providing an interactive web-based chat interface.
    *   Allows users to input natural language commands, view chat history, monitor sensor data, see current device states, and manage scheduled actions.
    *   Includes manual controls for direct device manipulation and a toggle for rule sets.

2.  **Artificial Intelligence (AI) Core (`app.py`, `sys_prompt.md`):**
    *   Designed for integration with various Large Language Models (LLMs) via **Ollama** for Natural Language Processing (NLP), enabling local and flexible deployment.
    *   `sys_prompt.md` defines the AI's persona, contextual awareness (sensor data, current actions, scheduled actions), and strict guidelines for generating responses (either JSON for actions/scheduling or natural language for conversational queries).
    *   Interprets user intent, applies contextual logic (e.g., "it's hot" implies fan action), and generates appropriate device commands or conversational replies.

3.  **Data Management (`app.py`, `utils.py`, `data.json`, `rule.json`, `scheduler.json`, `config.json`, `status.json`, `pending_updates.json`):**
    *   **`data.json`:** Stores the current state of sensors (light, temperature, humidity) and device actions (fan, light, speed, brightness). Managed by `DataManager` for safe read/write operations using `FileLock`.
    *   **`rule.json`:** Contains "fixed rules" (default automation logic) and "user preferences" (rules learned from user interactions). The `update_user_preference` function in `utils.py` dynamically updates these preferences based on sensor data and user-initiated actions.
    *   **`scheduler.json`:** Persists a list of all scheduled actions, including their unique IDs, target actions, scheduled execution times, and descriptions.
    *   **`config.json`:** A simple file storing the currently active rule set (`fixed_rule` or `user_preference`).
    *   **`status.json`:** Provides real-time system status updates, displayed in the UI.
    *   **`pending_updates.json`:** Temporarily stores messages or updates to be displayed in the UI, ensuring asynchronous updates are visible.
    *   All file operations utilize `FileLock` to prevent data corruption from concurrent access.

4.  **Communication Layer (MQTT) (`mqtt.py`):**
    *   A dedicated background thread that acts as an MQTT publisher.
    *   Connects to a local MQTT broker (e.g., `172.16.16.54:1883`).
    *   Continuously monitors `data.json` for changes in desired device actions.
    *   When changes are detected, it publishes corresponding JSON payloads to specific MQTT topics (e.g., "fan", "light") that hardware devices subscribe to.
    *   Updates `mqtt_status.json` with its operational status.

5.  **Hardware Integration (`hardware_control/esp32_subscriber/esp32_subscriber.ino`):**
    *   An Arduino sketch for an ESP32 microcontroller.
    *   Connects to the same WiFi network and MQTT broker.
    *   Subscribes to MQTT topics like "fan" and "light".
    *   The `callback` function processes incoming MQTT messages, parsing "on" or "off" commands, and directly controlling physical pins connected to devices (e.g., an LED for light, a digital pin for a fan).

6.  **Background Tasks (`app.py`, `update.py`, `mqtt.py`):**
    *   `app.py` initiates separate daemon threads for `background_task` (from `update.py`, likely for sensor data updates or other continuous checks) and `mqtt_background_task` (from `mqtt.py`).
    *   `execute_delayed_action` in `utils.py` uses `threading.Timer` to manage the execution of scheduled actions at precise times.

## Key Features

*   **Natural Language Interaction:** Control your home using conversational commands.
*   **Context-Aware Automation:** System responds intelligently based on sensor data (temperature, light) and implied needs.
*   **Action Scheduling:** Schedule devices to turn on/off or adjust at specific times or after delays.
*   **User Preference Learning:** The system adapts and learns your comfort preferences over time.
*   **Manual Device Control:** Direct control over fan speed and light brightness via the UI.
*   **Real-time Status:** Monitor current sensor readings, device states, and system updates.
*   **Robust Data Handling:** Utilizes file locking to ensure data integrity across concurrent operations.

## Conclusion

ComfortAI represents a step towards truly intelligent and responsive smart homes. By seamlessly integrating AI, robust data management, and reliable hardware communication, it provides an intuitive and powerful way to manage your home environment, ensuring your comfort is always prioritized.
