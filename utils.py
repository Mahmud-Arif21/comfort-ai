import streamlit as st
import json
import time
import threading
import os
from filelock import FileLock
from datetime import datetime

# Convert JSON actions to natural language
def json_to_natural_language(actions):
    if not actions:
        return "No changes made."
    
    messages = []
    for action in actions:
        atype = action.get('action_type')
        aval = action.get('action_value')
        if atype == "fan":
            messages.append(f"{'Turned on' if aval == 'on' else 'Turned off'} the fan")
        elif atype == "light":
            messages.append(f"{'Turned on' if aval == 'on' else 'Turned off'} the light")
        elif atype == "fan_speed":
            if int(aval) == 0:
                messages.append("Set fan speed to 0%")
            else:
                messages.append(f"Set fan speed to {aval}%")
        elif atype == "brightness":
            if int(aval) == 0:
                messages.append("Set brightness to 0%")
            else:
                messages.append(f"Set brightness to {aval}%")
        elif atype == "none":
            messages.append("No changes made")
    
    unique_messages = []
    seen = set()
    for msg in messages:
        if msg not in seen:
            unique_messages.append(msg)
            seen.add(msg)
    
    return ", ".join(unique_messages) if unique_messages else "No changes made"

# Update user_preference in rule.json based on sensor values and actions
def update_user_preference(data, actions, schedule_time=None):
    with FileLock("rule.json.lock"):
        try:
            rules = json.load(open("rule.json", 'r'))
            if 'fixed_rule' in rules:
                rules['fixed_rule'] = rules.get('fixed_rule', {})
            user_rules = rules['user_preference']
            sensors = data['sensors']
            current_time = datetime.now().strftime('%H:%M')
            time_range = schedule_time if schedule_time else ("06:00-18:00" if 6 <= int(current_time.split(':')[0]) <= 18 else "18:01-05:59")

            for action in actions:
                action_type = action.get('action_type')
                action_value = action.get('action_value')

                if action_type in ["fan", "fan_speed"]:
                    sensor = "temperature"
                    value = sensors.get("temperature", 32)
                    target_rules = user_rules.get("temperature", [])
                elif action_type in ["light", "brightness"]:
                    sensor = "light_level"
                    value = sensors.get("light_level", 80)
                    target_rules = user_rules.get("light_level", [])
                else:
                    continue

                matched_rule = None
                for rule in target_rules:
                    min_val = rule.get('min', float('-inf'))
                    max_val = rule.get('max', float('inf'))
                    rule_time = rule.get('time', '')
                    if min_val <= value <= max_val and (not rule_time or rule_time == time_range):
                        matched_rule = rule
                        break

                if not matched_rule:
                    new_rule = {
                        "label": f"{sensor}_{value}_{time_range.replace(':', '')}",
                        "min": value,
                        "max": value,
                        "time": time_range,
                        "actions": {}
                    }
                    target_rules.append(new_rule)
                    matched_rule = new_rule

                matched_rule['actions'] = matched_rule.get('actions', {})
                if action_type == "fan":
                    matched_rule['actions']['fan'] = action_value
                    if action_value == "off":
                        matched_rule['actions']['fan_speed'] = 0
                elif action_type == "fan_speed":
                    matched_rule['actions']['fan_speed'] = int(action_value)
                    if int(action_value) > 0:
                        matched_rule['actions']['fan'] = "on"
                elif action_type == "light":
                    matched_rule['actions']['light'] = action_value
                    if action_value == "off":
                        matched_rule['actions']['set_brightness'] = 0
                elif action_type == "brightness":
                    matched_rule['actions']['set_brightness'] = int(action_value)
                    if int(action_value) > 0:
                        matched_rule['actions']['light'] = "on"

            with open("rule.json", 'w') as f:
                json.dump(rules, f, indent=4)
        except Exception as e:
            print(f"Error updating user preferences: {e}")

# Load pending updates from file
def load_pending_updates():
    with FileLock("pending_updates.json.lock"):
        try:
            if os.path.exists("pending_updates.json"):
                with open("pending_updates.json", 'r') as f:
                    return json.load(f)
            return []
        except Exception:
            return []

# Save pending updates to file
def save_pending_updates(updates):
    with FileLock("pending_updates.json.lock"):
        try:
            with open("pending_updates.json", 'w') as f:
                json.dump(updates, f, indent=2)
        except Exception as e:
            print(f"Error saving pending updates: {e}")

# Update config.json
def update_config(rule_set):
    config = {"active_rule_set": rule_set}
    with FileLock("config.json.lock"):
        try:
            with open("config.json", 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error updating config: {e}")

# Load scheduled actions from scheduler.json
def load_scheduled_actions():
    with FileLock("scheduler.json.lock"):
        try:
            if os.path.exists("scheduler.json"):
                with open("scheduler.json", 'r') as f:
                    data = json.load(f)
                    return data.get('scheduled_actions', [])
            return []
        except Exception:
            return []

# Save scheduled actions to scheduler.json
def save_scheduled_actions(scheduled_actions):
    with FileLock("scheduler.json.lock"):
        try:
            with open("scheduler.json", 'w') as f:
                json.dump({"scheduled_actions": scheduled_actions}, f, indent=2)
        except Exception as e:
            print(f"Error saving scheduled actions: {e}")

# Execute delayed actions
def execute_delayed_action(data, data_manager, actions, delay_seconds, rule_set, action_id, schedule_time_str=None):
    def apply_actions():
        nonlocal data
        current_actions = data.get('action', {}).copy()
        for act in actions:
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
        update_user_preference(data, actions, schedule_time_str)
        data_manager.update_data(data)
        update_config(rule_set)
        natural_language_response = json_to_natural_language(actions)
        scheduled_actions = load_scheduled_actions()
        action = next((sa for sa in scheduled_actions if sa["id"] == action_id), None)
        display_time = schedule_time_str if schedule_time_str else f"after {delay_seconds} seconds"
        timestamp = time.time()
        updates = load_pending_updates()
        updates.append({"text": f"Action executed at {datetime.now().strftime('%H:%M:%S')} ({display_time}): {natural_language_response}", "timestamp": timestamp})
        save_pending_updates(updates)
        scheduled_actions = [sa for sa in scheduled_actions if sa["id"] != action_id]
        save_scheduled_actions(scheduled_actions)
        # Removed: st.session_state.scheduled_actions = scheduled_actions

    description = json_to_natural_language(actions)
    scheduled_time = time.time() + delay_seconds
    scheduled_actions = load_scheduled_actions()
    scheduled_actions.append({
        "id": action_id,
        "actions": actions,
        "delay_seconds": delay_seconds,
        "scheduled_time": scheduled_time,
        "description": description,
        "schedule_type": "Specific Time" if schedule_time_str else "Delay (seconds)",
        "schedule_time_str": schedule_time_str
    })
    save_scheduled_actions(scheduled_actions)
    st.session_state.scheduled_actions = scheduled_actions
    st.session_state.display_history.append({"role": "model", "text": f"Scheduled to perform actions ({description}) {schedule_time_str if schedule_time_str else f'in {delay_seconds} seconds'}."})

    timer = threading.Timer(delay_seconds, apply_actions)
    timer.start()