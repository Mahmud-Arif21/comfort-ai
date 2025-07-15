import streamlit as st
import json
import os
from filelock import FileLock
import time
import re
import uuid
from utils import execute_delayed_action, json_to_natural_language, load_scheduled_actions, save_scheduled_actions
from datetime import datetime

# Path to rules, config, and status files
RULES_FILE = 'rule.json'
RULES_LOCK_FILE = RULES_FILE + '.lock'
CONFIG_FILE = 'config.json'
CONFIG_LOCK_FILE = CONFIG_FILE + '.lock'
STATUS_FILE = 'status.json'
STATUS_LOCK_FILE = STATUS_FILE + '.lock'

# Helper to update config.json when rule_set changes
def write_config(active_rule_set):
    try:
        with FileLock(CONFIG_LOCK_FILE):
            with open(CONFIG_FILE, 'w') as cf:
                json.dump({"active_rule_set": active_rule_set}, cf, indent=4)
    except Exception as e:
        st.error(f"Could not update config: {e}")

# Helper to load status from status.json
def load_status(file_path, lock_file):
    try:
        with FileLock(lock_file):
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    return data.get('status', 'No status available')
            return 'No status available'
    except Exception as e:
        return f"Error loading status: {e}"

# Helper to update user_preference rules with time ranges
def update_rule_time(sensor, label, new_time):
    try:
        with FileLock(RULES_LOCK_FILE):
            rules = json.load(open(RULES_FILE, 'r'))
            target_rules = rules['user_preference'].get(sensor, [])
            for rule in target_rules:
                if rule['label'] == label:
                    if new_time:
                        rule['time'] = new_time
                    else:
                        rule.pop('time', None)
                    break
            with open(RULES_FILE, 'w') as f:
                json.dump(rules, f, indent=4)
        st.success(f"Updated time range for {sensor} rule: {label}")
    except Exception as e:
        st.error(f"Failed to update rule time: {e}")

# Helper to format time for display
def format_schedule_time(scheduled_action, current_time):
    time_left = max(0, scheduled_action["scheduled_time"] - current_time)
    if time_left <= 1:
        return "soon"
    if scheduled_action.get("schedule_time_str"):
        return scheduled_action["schedule_time_str"]
    if time_left >= 3600:
        hours = int(time_left // 3600)
        return f"{hours} hour{'s' if hours > 1 else ''}"
    elif time_left >= 60:
        minutes = int(time_left // 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''}"
    else:
        return f"{int(time_left)} second{'s' if time_left != 1 else ''}"

# Predefined actions for the dropdown
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

def render_ui(data, data_manager, process_user_input):
    # Layout Columns
    main_col, right_col = st.columns([3, 1])

    # Main Chat Area
    with main_col:
        st.header("Comfort AI")

        # Render chat history
        st.markdown(
            """
            <style>
            #chat-container {
                height: 60vh;
                overflow-y: auto;
                padding: 10px;
                border: 1px solid #444;
                border-radius: 8px;
                background-color: #1e1e1e;
                color: #e0e0e0;
                display: flex;
                flex-direction: column-reverse;
            }
            .chat-user {
                background-color: #2b2b5f;
                padding: 10px;
                margin-bottom: 8px;
                border-radius: 6px;
                border-left: 4px solid #4f8edc;
            }
            .chat-model {
                background-color: #3a1f1f;
                padding: 10px;
                margin-bottom: 8px;
                border-radius: 6px;
                border-left: 4px solid #d47070;
            }
            .status-container {
                background-color: #2a2a2a;
                padding: 12px;
                border-radius: 6px;
                border: 1px solid #555;
                font-size: 13px;
                color: #e0e0e0;
                line-height: 1.5;
                margin-bottom: 10px;
            }
            .status-container p {
                margin: 0;
            }
            </style>
            """, unsafe_allow_html=True)
        chat_html = '<div id="chat-container">'
        sorted_history = sorted(st.session_state.display_history, key=lambda x: x.get("timestamp", 0), reverse=True)
        for msg in sorted_history:
            cls = "chat-user" if msg["role"] == "user" else "chat-model"
            chat_html += f'<div class="{cls}"><strong>{msg["role"].capitalize()}:</strong><br>{msg["text"]}</div>'
        chat_html += '</div>'
        st.markdown(chat_html, unsafe_allow_html=True)

        # Capture user input
        user_input = st.chat_input("Ask something...")
        if user_input:
            data = process_user_input(user_input, data, data_manager)

    # Sidebar: Rule Set Toggle and Controls
    with st.sidebar:
        st.subheader("Rule Set")
        rule_set = st.radio(
            "Select Rule Set:",
            ["Fixed Rule", "User Preference"],
            index=0 if st.session_state.get('rule_set', 'fixed_rule') == 'fixed_rule' else 1,
            key="rule_set_toggle"
        )
        new_set = 'fixed_rule' if rule_set == "Fixed Rule" else 'user_preference'
        if new_set != st.session_state.get('rule_set'):
            st.session_state.rule_set = new_set
            write_config(new_set)

        if st.button("Reset Preference"):
            try:
                with FileLock(RULES_LOCK_FILE):
                    rules = json.load(open(RULES_FILE, 'r'))
                    rules['user_preference'] = rules['fixed_rule']
                    with open(RULES_FILE, 'w') as f:
                        json.dump(rules, f, indent=4)
                st.success("User preferences reset to match fixed rules.")
            except Exception as e:
                st.error(f"Failed to reset preferences: {e}")

        with st.expander("⏰ Schedule Editor", expanded=False):
            st.subheader("Schedule New Action")
            schedule_type = st.radio("Schedule Type:", ["Delay (seconds)", "Specific Time"], key="schedule_type")
            action_name = st.selectbox("Select Action:", list(PREDEFINED_ACTIONS.keys()), key="schedule_action_select_editor")

            schedule_time_str = None
            if schedule_type == "Delay (seconds)":
                delay_seconds = st.number_input("Delay (seconds):", min_value=1, value=10, key="schedule_delay_input_editor")
                schedule_time = None
            else:
                schedule_time_str = st.text_input("Schedule Time (HH:MM, e.g., 14:30):", key="schedule_time_input")
                delay_seconds = None
                if schedule_time_str and not re.match(r'^\d{2}:\d{2}$', schedule_time_str):
                    st.error("Invalid time format. Use HH:MM (e.g., 14:30).")
                    schedule_time = None
                else:
                    try:
                        schedule_time = datetime.strptime(schedule_time_str, '%H:%M').time()
                        now = datetime.now()
                        schedule_datetime = datetime.combine(now.date(), schedule_time)
                        if schedule_datetime < now:
                            schedule_datetime = schedule_datetime.replace(day=now.day + 1)
                        delay_seconds = (schedule_datetime - now).total_seconds()
                        if delay_seconds < 0:
                            st.error("Scheduled time must be in the future.")
                            schedule_time = None
                            delay_seconds = None
                    except ValueError:
                        st.error("Invalid time format. Use HH:MM (e.g., 14:30).")
                        schedule_time = None
                        delay_seconds = None

            if st.button("Schedule Action", key="schedule_action_button_editor") and (delay_seconds is not None):
                actions = PREDEFINED_ACTIONS[action_name]
                try:
                    with FileLock(CONFIG_LOCK_FILE):
                        config = json.load(open(CONFIG_FILE, 'r'))
                        active_rule_set = config.get('active_rule_set', 'fixed_rule')
                except Exception:
                    active_rule_set = 'fixed_rule'
                action_id = str(uuid.uuid4())
                description = json_to_natural_language(actions)
                scheduled_actions = load_scheduled_actions()
                scheduled_time_epoch = time.time() + delay_seconds
                if not any(sa["id"] == action_id for sa in scheduled_actions):
                    scheduled_actions.append({
                        "id": action_id,
                        "actions": actions,
                        "delay_seconds": delay_seconds,
                        "scheduled_time": scheduled_time_epoch,
                        "description": description,
                        "schedule_type": schedule_type,
                        "schedule_time_str": schedule_time_str if schedule_type == "Specific Time" else None
                    })
                    save_scheduled_actions(scheduled_actions)
                    st.session_state.scheduled_actions = scheduled_actions
                    display_time = schedule_time_str if schedule_type == "Specific Time" else f"in {delay_seconds} seconds"
                    st.session_state.display_history.append({"role": "model", "text": f"Scheduled to perform actions ({description}) {display_time}.", "timestamp": time.time()})
                    execute_delayed_action(data, data_manager, actions, delay_seconds, active_rule_set, action_id, schedule_time_str)

        st.markdown("---")

        with st.container():
            with st.expander("🔧 Settings", expanded=False):
                st.subheader("System Prompt")
                user_sys = st.text_area("Custom system prompt:", value="", height=120)
                if st.button("Save Prompt"):
                    if user_sys.strip():
                        st.session_state.system_prompt = user_sys
                        st.success("Saved system prompt.")
                    else:
                        st.warning("Prompt cannot be empty.")

                st.markdown("---")
                st.subheader("Sensors (Read-Only)")
                st.markdown(f"**Light:** {data['sensors']['light_level']}")
                st.markdown(f"**Temp:** {data['sensors']['temperature']}°C")
                st.markdown(f"**Humidity:** {data['sensors']['humidity']}%")
                st.markdown("*Note: Sensor values are managed by the system and cannot be modified through the UI.*")

                st.markdown("---")
                st.subheader("Current Status")
                action_state = st.session_state.get('action_state', data['action'])
                st.markdown(f"**Fan:** {action_state['fan'].capitalize()}")
                st.markdown(f"**Speed:** {action_state['fan_speed']}%")
                st.markdown(f"**Light:** {action_state['light'].capitalize()}")
                st.markdown(f"**Brightness:** {action_state['set_brightness']}%")

        with st.expander("🎛️ Manual Controls", expanded=False):
            st.subheader("Fan Control")
            fan_stat = st.selectbox("Fan:", ["on", "off"], index=["on", "off"].index(st.session_state.get('action_state', data['action'])['fan']), key="fan_select")
            fan_spd = st.slider("Speed:", 0, 100, st.session_state.get('action_state', data['action'])['fan_speed'], key="fan_speed_slider")

            st.subheader("Light Control")
            light_stat = st.selectbox("Light:", ["on", "off"], index=["on", "off"].index(st.session_state.get('action_state', data['action'])['light']), key="light_select")
            bright = st.slider("Brightness:", 0, 100, st.session_state.get('action_state', data['action'])['set_brightness'], key="brightness_slider")

            if st.button("Update", key="manual_update"):
                data['action'] = {
                    "fan": fan_stat,
                    "fan_speed": fan_spd,
                    "light": light_stat,
                    "set_brightness": bright
                }
                data_manager.update_data(data)
                data = data_manager.load_data()
                st.session_state['action_state'] = data['action']
                st.success("Settings updated!")
                st.rerun()

    # Right Column: Status Displays
    with right_col:
        st.subheader("System Update")
        update_status = load_status(STATUS_FILE, STATUS_LOCK_FILE)
        update_status_html = update_status.replace('\n', '<br>')
        st.markdown(f'<div class="status-container"><p>{update_status_html}</p></div>', unsafe_allow_html=True)

        st.subheader("Scheduled Actions")
        scheduled_actions = st.session_state.get('scheduled_actions', [])
        if scheduled_actions:
            current_time = time.time()
            for sa in scheduled_actions:
                display_time = format_schedule_time(sa, current_time)
                st.write(f"{sa['description']} - {display_time}")
        else:
            st.write("No scheduled actions.")

    return data