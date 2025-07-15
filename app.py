import os
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai
import json
import re
import threading
import uuid
from ui import render_ui
from utils import execute_delayed_action, load_pending_updates, save_pending_updates, load_scheduled_actions, save_scheduled_actions, json_to_natural_language, update_config, update_user_preference
from update import background_task
from mqtt import mqtt_background_task
from filelock import FileLock
from datetime import datetime
import time

# Streamlit Page Config (must be the first Streamlit command)
st.set_page_config(page_title="ComfortAI", page_icon="🛜", layout="wide")

# Load environment variables
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# Predefined actions
PREDEFINED_ACTIONS = {
    "Turn on everything": [
        {"action_type": "fan", "action_value": "on"},
        {"action_type": "fan_speed", "action_value": "100"},
        {"action_type": "light", "action_value": "on"},
        {"action_type": "brightness", "action_value": "100"}
    ],
    "Turn off everything": [
        {"action_type": "fan", "action_value": "off"},
        {"action_type": "fan_speed", "action_value": "0"},
        {"action_type": "light", "action_value": "off"},
        {"action_type": "brightness", "action_value": "0"}
    ],
    "Turn on the fan": [
        {"action_type": "fan", "action_value": "on"},
        {"action_type": "fan_speed", "action_value": "50"}
    ],
    "Turn off the fan": [
        {"action_type": "fan", "action_value": "off"},
        {"action_type": "fan_speed", "action_value": "0"}
    ],
    "Turn on the light": [
        {"action_type": "light", "action_value": "on"},
        {"action_type": "brightness", "action_value": "50"}
    ],
    "Turn off the light": [
        {"action_type": "light", "action_value": "off"},
        {"action_type": "brightness", "action_value": "0"}
    ]
}

# Data Management Module
class DataManager:
    def __init__(self, data_path):
        self.data_path = data_path
        self.lock_file = data_path + '.lock'
        self.ensure_data_file()

    def ensure_data_file(self):
        with FileLock(self.lock_file):
            if not os.path.exists(self.data_path):
                os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
                default_data = {
                    "sensors": {"light_level": 80, "temperature": 32, "humidity": 50},
                    "action": {"fan": "on", "fan_speed": 100, "light": "off", "set_brightness": 0}
                }
                self.update_data(default_data)

    def load_data(self):
        with FileLock(self.lock_file):
            try:
                with open(self.data_path, 'r') as f:
                    return json.load(f)
            except Exception:
                return self.get_default_data()

    def update_data(self, data):
        with FileLock(self.lock_file):
            try:
                with open(self.data_path, 'w') as f:
                    json.dump(data, f, indent=2)
                return True
            except Exception as e:
                st.error(f"Error updating data: {e}")
                return False

    def get_default_data(self):
        return {
            "sensors": {"light_level": 80, "temperature": 32, "humidity": 50},
            "action": {"fan": "on", "fan_speed": 100, "light": "off", "set_brightness": 0}
        }

# Configure Gemini API
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# Initialize session state
if "chat_session" not in st.session_state:
    try:
        with open('sys_prompt.md', 'r') as f:
            system_prompt = f.read()
        st.session_state.chat_session = model.start_chat(history=[{
            "role": "user",
            "parts": [system_prompt]
        }])
    except FileNotFoundError:
        st.error("System prompt file (sys_prompt.md) not found.")
        st.session_state.chat_session = model.start_chat(history=[])

if "display_history" not in st.session_state:
    st.session_state.display_history = []

if "rule_set" not in st.session_state:
    st.session_state.rule_set = "fixed_rule"

if "last_check" not in st.session_state:
    st.session_state.last_check = time.time()

# Load session state from scheduler.json
if os.path.exists("scheduler.json"):
    st.session_state.scheduled_actions = load_scheduled_actions()

# Handle UI cancellation
if "cancel_action" in st.session_state:
    action_id = st.session_state.cancel_action
    scheduled_actions = load_scheduled_actions()
    action_to_cancel = next((sa for sa in scheduled_actions if sa["id"] == action_id), None)
    if action_to_cancel:
        description = action_to_cancel["description"]
        updated_actions = [sa for sa in scheduled_actions if sa["id"] != action_id]
        save_scheduled_actions(updated_actions)
        st.session_state.scheduled_actions = updated_actions
        st.session_state.display_history.append({"role": "model", "text": f"Scheduled action canceled: {description}", "timestamp": time.time()})
    del st.session_state.cancel_action
    st.rerun()

# Start background task
if "background_task_started" not in st.session_state:
    st.session_state.background_task_started = True
    
    bg_thread = threading.Thread(target=background_task, daemon=True)
    bg_thread.start()
    
    mqtt_thread = threading.Thread(target=mqtt_background_task, daemon=True)
    mqtt_thread.start()

# Data Manager
data_manager = DataManager('data.json')
data = data_manager.load_data()

# Process user input
def process_user_input(user_input, data, data_manager):
    if user_input:
        st.session_state.display_history.append({"role": "user", "text": user_input, "timestamp": time.time()})

        try:
            with FileLock("config.json.lock"):
                config = json.load(open("config.json", 'r'))
                active_rule_set = config.get('active_rule_set', 'fixed_rule')
        except Exception:
            active_rule_set = 'fixed_rule'

        current_time = datetime.now().strftime('%H:%M')
        context = (
            f"Current system state:\n"
            f"- Current Time: {current_time}\n"
            f"- Sensors: Light: {data['sensors']['light_level']}, Temp: {data['sensors']['temperature']}°C, Humidity: {data['sensors']['humidity']}%\n"
            f"- Actions: Fan: {data['action']['fan'].capitalize()}, Speed: {data['action']['fan_speed']}%, Light: {data['action']['light'].capitalize()}, Brightness: {data['action']['set_brightness']}%\n"
            f"- Active Rule Set: {'Fixed Rules' if active_rule_set == 'fixed_rule' else 'User Preferences'}\n"
            f"- Scheduled actions: {json.dumps(st.session_state.get('scheduled_actions', []), indent=2)}\n"
            f"User query: {user_input}\n"
            f"Predefined actions: {json.dumps(PREDEFINED_ACTIONS, indent=2)}\n"
            f"Note: For scheduling, use predefined actions or specify actions like fan, light, fan_speed, or brightness with delay (seconds) or specific time (HH:MM)."
        )

        try:
            resp = st.session_state.chat_session.send_message(context)
            text = resp.text.strip()

            # Check for scheduling intent
            delay_match = re.search(r"(?:in|after)\s+(\d+)\s*(?:seconds?|mins?|minutes?|hours?)", user_input.lower())
            time_match = re.search(r"at\s+(\d{2}:\d{2})", user_input.lower())
            schedule_time_str = None
            delay_seconds = None

            if delay_match or time_match:
                if delay_match:
                    delay_seconds = int(delay_match.group(1))
                    if "hour" in user_input.lower():
                        delay_seconds *= 3600
                    elif "minute" in user_input.lower():
                        delay_seconds *= 60
                elif time_match:
                    schedule_time_str = time_match.group(1)
                    try:
                        schedule_time = datetime.strptime(schedule_time_str, '%H:%M').time()
                        now = datetime.now()
                        schedule_datetime = datetime.combine(now.date(), schedule_time)
                        if schedule_datetime < now:
                            schedule_datetime = schedule_datetime.replace(day=now.day + 1)
                        delay_seconds = (schedule_datetime - now).total_seconds()
                        if delay_seconds < 0:
                            raise ValueError("Scheduled time must be in the future.")
                    except ValueError as e:
                        st.session_state.display_history.append({"role": "model", "text": f"Invalid time format or past time: {e}. Use HH:MM (e.g., 14:30).", "timestamp": time.time()})
                        st.rerun()
                        return data

                # Check for predefined action in user input
                for action_name, actions in PREDEFINED_ACTIONS.items():
                    if action_name.lower() in user_input.lower():
                        action_id = str(uuid.uuid4())  # Use UUID for unique ID
                        scheduled_actions = load_scheduled_actions()
                        if not any(sa["id"] == action_id for sa in scheduled_actions):
                            execute_delayed_action(data, data_manager, actions, delay_seconds, active_rule_set, action_id, schedule_time_str)
                            description = json_to_natural_language(actions)
                            display_time = schedule_time_str if schedule_time_str else f"in {delay_seconds} seconds"
                            st.session_state.display_history.append({"role": "model", "text": f"Scheduled to perform {action_name} ({description}) {display_time}.", "timestamp": time.time()})
                        st.rerun()
                        return data

                # Parse JSON response for actions
                match = re.search(r'(\[\s*\{.*?\}\s*\]|\{.*?\})', text, re.DOTALL)
                if match:
                    json_text = match.group(0)
                    try:
                        actions = json.loads(json_text)
                        if isinstance(actions, dict):
                            actions = [actions]

                        action_id = str(uuid.uuid4())  # Use UUID for unique ID
                        scheduled_actions = load_scheduled_actions()
                        if not any(sa["id"] == action_id for sa in scheduled_actions):
                            execute_delayed_action(data, data_manager, actions, delay_seconds, active_rule_set, action_id, schedule_time_str)
                            description = json_to_natural_language(actions)
                            display_time = schedule_time_str if schedule_time_str else f"in {delay_seconds} seconds"
                            st.session_state.display_history.append({"role": "model", "text": f"Scheduled to perform actions ({description}) {display_time}.", "timestamp": time.time()})
                        st.rerun()
                        return data
                    except json.JSONDecodeError:
                        st.session_state.display_history.append({"role": "model", "text": "Sorry, I couldn't process that scheduling request. Please try again.", "timestamp": time.time()})
                        st.rerun()
                        return data

            # Handle immediate actions, rule set changes, or cancellations
            match = re.search(r'(\[\s*\{.*?\}\s*\]|\{.*?\})', text, re.DOTALL)
            if match:
                json_text = match.group(0)
                try:
                    actions = json.loads(json_text)
                    if isinstance(actions, dict):
                        actions = [actions]

                    # Filter actions by type
                    device_actions = [act for act in actions if act.get('action_type') in ["fan", "light", "brightness", "fan_speed", "none"]]
                    cancel_actions = [act for act in actions if act.get('action_type') == "cancel_scheduled" and act.get('action_value') == "all"]
                    rule_set_actions = [act for act in actions if act.get('action_type') == "rule_set"]

                    # Handle cancellations
                    if cancel_actions:
                        scheduled_actions = []
                        save_scheduled_actions(scheduled_actions)
                        st.session_state.scheduled_actions = scheduled_actions
                        st.session_state.display_history.append({"role": "model", "text": "All scheduled actions have been canceled.", "timestamp": time.time()})

                    # Handle rule set changes
                    if rule_set_actions:
                        active_rule_set = rule_set_actions[0].get('action_value')
                        update_config(active_rule_set)
                        st.session_state.display_history.append({"role": "model", "text": f"Rule set changed to {active_rule_set}", "timestamp": time.time()})

                    # Handle device actions
                    if device_actions:
                        current_actions = data.get('action', {}).copy()
                        for act in device_actions:
                            atype, aval = act.get('action_type'), act.get('action_value')
                            if atype == "fan":
                                current_actions['fan'] = aval
                                if aval == 'off': current_actions['fan_speed'] = 0
                            elif atype == "light":
                                current_actions['light'] = aval
                                if aval == 'off': current_actions['set_brightness'] = 0
                            elif atype == "brightness":
                                lvl = int(aval)
                                current_actions['set_brightness'] = lvl
                                if lvl > 0: current_actions['light'] = 'on'
                            elif atype == "fan_speed":
                                lvl = int(aval)
                                current_actions['fan_speed'] = lvl
                                if lvl > 0: current_actions['fan'] = 'on'
                        data['action'] = current_actions
                        update_user_preference(data, device_actions)
                        data_manager.update_data(data)
                        data = data_manager.load_data()
                        st.session_state['action_state'] = data['action']
                        st.session_state.display_history.append({"role": "model", "text": json_to_natural_language(device_actions), "timestamp": time.time()})

                    st.rerun()
                    return data
                except json.JSONDecodeError:
                    st.session_state.display_history.append({"role": "model", "text": "Sorry, I couldn't process that action. Please try again.", "timestamp": time.time()})
                    st.rerun()
                    return data

            # Handle conversational responses
            st.session_state.display_history.append({"role": "model", "text": text, "timestamp": time.time()})
            st.rerun()  # Force UI refresh after conversational response
            return data

        except Exception as e:
            error_message = f"Sorry, something went wrong. Please try again. Error: {e}"
            st.session_state.display_history.append({"role": "model", "text": error_message, "timestamp": time.time()})
            st.rerun()
            return data

    return data

# Check for pending updates and scheduled actions in the main thread
current_time = time.time()
if current_time - st.session_state.last_check >= 0.1:
    st.session_state.last_check = current_time
    scheduled_actions = load_scheduled_actions()
    st.session_state.scheduled_actions = scheduled_actions
    updates = load_pending_updates()
    if updates:
        for update in sorted(updates, key=lambda x: x["timestamp"]):
            st.session_state.display_history.append({"role": "model", "text": update["text"], "timestamp": update["timestamp"]})
        save_pending_updates([])
        st.rerun()

# Render UI
data = render_ui(data, data_manager, process_user_input)