# Comfort AI

environmental conditions based on sensor data and user preferences. It uses sensors to monitor light levels, temperature, and humidity, and controls devices like fans and lights via an MQTT broker. The system features a user-friendly chat interface using Gemini API Key for natural language interaction and supports scheduling of actions.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.8 or higher**: Download and install from [python.org](https://www.python.org/downloads/).
- **pip**: Python package manager, usually included with Python.
- **Git**: For cloning the repository, install from [git-scm.com](https://git-scm.com/downloads).

## Setup

Follow these steps to set up the project on your computer:

1. **Clone the Repository**

   Open a terminal or command prompt and run:

   ```bash
   git clone https://github.com/Mahmud-Arif21/comfort-ai.git
   cd comfort-ai
   ```


2. **Install Required Python Packages**

   Create a file named `requirements.txt` in the `comfort-ai` directory with the following content:

   ```
   streamlit
   google-generativeai
   paho-mqtt
   filelock
   python-dotenv
   ```

   Then, install the packages by running:

   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up Your Gemini API Key and MQTT Broker**

   - Obtain a Gemini API key from the [Google AI Studio](https://aistudio.google.com/app/apikey).
   - Create a file named `.env` in the `comfort-ai` directory with the following content:

     ```
     GEMINI_API_KEY=your_api_key_here
     MQTT_BROKER_IP=your_mqtt_broker_ip
     ```

   - If your MQTT broker requires authentication, add:

     ```
     MQTT_USER=your_username
     MQTT_PASSWORD=your_password
     ```

   - Replace `your_api_key_here` with your actual Gemini API key, and `your_mqtt_broker_ip` with the IP address of your MQTT broker.

4. **Set Up an MQTT Broker**

   - Install an MQTT broker (e.g., Mosquitto) on a device on your network.
   - Ensure it is running and accessible from the device running Comfort AI.
   - Note the IP address of the broker and set it in the `.env` file as `MQTT_BROKER_IP`.
   - If using Mosquitto, you can install it on Windows, Mac, or Linux. For example, on Ubuntu, run `sudo apt install mosquitto mosquitto-clients`, then start it with `mosquitto`.
   - If your broker is on the same machine as Comfort AI, you can use `localhost` or `127.0.0.1`.

5. **ESP32 Device Setup**

   - For the ESP32 device, upload the provided `hardware_control/esp32_subscriber/esp32_subscriber.ino` sketch, replacing the placeholders with your WiFi credentials and MQTT broker IP.
   - Ensure the ESP32 and the Comfort AI system are on the same network and can reach the MQTT broker.
 
 **Note:** At this point actual sensors are not used, so the ESP32 is not publishing to the mqtt broker. Once the sensors are in hand, the scripts will be updated.

## Running the Application

1. **Start the Streamlit App**

   In the `comfort-ai` directory, run:

   ```bash
   streamlit run app.py
   ```

   This launches the web interface.

2. **Access the Application**

   Open your web browser and go to:

   ```
   http://localhost:8501
   ```

   You should see the Comfort AI interface.

## Features

- **Automatic Control**: Adjusts fan and light settings based on sensor data and predefined rules.
- **Chat Interface**: Use natural language to control devices or query status.
- **Scheduling**: Schedule actions for specific times or delays.
- **Rule Sets**: Switch between "Fixed Rule" (default settings) and "User Preference" (custom settings).

## Usage

### 1. Chat Interface

- Type commands, questions or just chat naturally in the chat input box at the bottom of the main screen. Examples:
  - **Direct Command:** "Turn on the fan" => `fan turns on`
  - **Question:** "What's the current temperature?" => `status update`
  - **Order Schedule:** "Schedule turn off everything in 10 minutes" => `schedules the action`
  - **Chat Normally:** "I'm going to bed now." => `turns light off`

### 2. Manual Controls

- In the sidebar, use the "Manual Controls" section:
  - Adjust **Fan** (on/off) and **Speed** (0-100%) with dropdowns and sliders.
  - Adjust **Light** (on/off) and **Brightness** (0-100%) similarly.
  - Click **Update** to apply changes.

### 3. Scheduling

- In the sidebar, expand "Schedule Editor":
  - Choose a predefined action (e.g., "Turn on the fan") from the dropdown.
  - Select "Delay (seconds)" or "Specific Time" (e.g., 14:30) and enter the time.
  - Click **Schedule Action** to set it.

### 4. Rule Set

- In the sidebar, under "Rule Set":
  - Switch between "Fixed Rule" and "User Preference" using the radio buttons. Fixed rules are sensor-action relations based on general estimations.
  - "User Preference" updates as you ask for specific changes over time.
  - Click "Reset Preference" to revert "User Preference" to match "Fixed Rule".

## Project Structure

Here's what each file does:

- `app.py`: Main Streamlit application.
- `ui.py`: User interface components.
- `update.py`: Background task for updating device actions based on rules.
- `mqtt.py`: MQTT publisher for sending actions to devices.
- `utils.py`: Utility functions.
- `data.json`: Stores current sensor data and device actions. 
- `rule.json`: Defines rules for device control.
- `config.json`: Configuration file, including the active rule set.
- `scheduler.json`: Stores scheduled actions.
- `sys_prompt.md`: System prompt for the AI model that defines the behavior and personality of the chat interface, enabling natural language interaction with the home automation system.

**Note:** Since the ESP32 does not publish sensor data at this moment, `data.json` uses dummy data.  Once the sensors are in hand, this will also be updated.

## Customizing Rules

To tweak how the system responds to sensor data:

- Open `rule.json` in a text editor.
- It has two sections: `fixed_rule` and `user_preference`.
- Each rule specifies conditions (e.g., temperature range, time) and actions (e.g., fan speed).
- Edit `user_preference` to customize behavior. Example:
  ```json
  {
    "label": "warm",
    "min": 31,
    "max": 33,
    "actions": {
      "fan": "on",
      "fan_speed": 80
    }
  }
  ```
- Save the file; changes apply when the app updates (every second).

## Future Improvements

The Comfort AI system is designed to be extensible and has several planned enhancements:

### Sensor Expansion
- **Current Sensor**: Monitor electrical usage and power consumption to optimize energy efficiency
- **Gas Sensor**: Detect air quality and gas levels for enhanced safety and environmental monitoring
- **Motion Sensor**: Implement presence detection for automatic room control

### Enhanced Interaction
- **Voice Chat Integration**: Natural voice commands and responses for hands-free control
- **Multi-language Support**: Expand chat interface to support multiple languages
- **Mobile App**: Dedicated mobile application for remote control and monitoring
- **Gesture Control**: Integration with gesture recognition for touchless operation

### Advanced Features
- **Machine Learning**: Predictive automation based on usage patterns and user behavior
- **Home Appliances Damage Alert**: Monitoring if the lights, fans, fridge etc. are working properly or not and notifying user.
- **Multi-room Support**: Extend control to multiple rooms and zones
- **Smart Scheduling**: Scheduling that learns from user preferences
- **Energy Analytics**: Detailed energy consumption reports and optimization suggestions

### Device Integration
- **Smart Appliances**: Control of additional devices like air conditioners, heaters, and fridges
- **Smart Switch Board**: Get the whole control inside a switch board.

## Troubleshooting

- **MQTT Connection Issues**: Ensure your MQTT broker is running and the address in `.env` matches it. Check network connectivity.
- **API Key Errors**: Verify your Google API key in `.env` is correct and active.
- **File Lock Errors**: If you see file access issues, ensure no other process is using the JSON files (e.g., close editors).
- **Streamlit Not Starting**: Confirm all packages are installed (`pip install -r requirements.txt`) and there are no typos in `app.py`.

If you encounter other issues, check the terminal for error messages or restart the app.

---

Enjoy using Comfort AI to make your home smarter and more comfortable!

**Note**: The system publishes to MQTT topics based on the keys in the 'action' dictionary in `data.json`. By default, it uses 'fan' and 'light'. Ensure your devices are subscribed to these topics or adjust the topics in `data.json` and your device code accordingly.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
