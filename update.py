import json
import time
import os
from filelock import FileLock
from datetime import datetime

# Configuration
RULES_FILE = 'rule.json'
DATA_FILE = 'data.json'
CONFIG_FILE = 'config.json'
LOCK_FILE = 'data.json.lock'
CONFIG_LOCK_FILE = 'config.json.lock'
STATUS_FILE = 'status.json'
STATUS_LOCK_FILE = 'status.json.lock'
UPDATE_INTERVAL = 1  # Update interval in seconds

def load_json(path, lock_file=None):
    """Load JSON data from a file."""
    if lock_file:
        with FileLock(lock_file):
            with open(path, 'r') as f:
                return json.load(f)
    with open(path, 'r') as f:
        return json.load(f)

def save_json(path, data, lock_file=None):
    """Save JSON data to a file, preserving formatting."""
    if lock_file:
        with FileLock(lock_file):
            # Optionally, back up the old data
            backup = path + '.bak'
            if os.path.exists(path):
                os.replace(path, backup)
            with open(path, 'w') as f:
                json.dump(data, f, indent=4)
    else:
        # Optionally, back up the old data
        backup = path + '.bak'
        if os.path.exists(path):
            os.replace(path, backup)
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)

def is_time_in_range(time_str, current_time):
    """Check if current_time (HH:MM) is within the time range (HH:MM-HH:MM)."""
    if not time_str:
        return True  # No time range means rule applies all the time
    try:
        start_str, end_str = time_str.split('-')
        start = datetime.strptime(start_str, '%H:%M').time()
        end = datetime.strptime(end_str, '%H:%M').time()
        current = datetime.strptime(current_time, '%H:%M').time()
        
        if start <= end:
            return start <= current <= end
        else:  # Handles ranges that cross midnight (e.g., 22:00-06:00)
            return current >= start or current <= end
    except ValueError:
        return False  # Invalid time format, skip rule

def get_actions_for(sensor_name, value, rules, active_rule_set):
    """
    Determine the actions for a given sensor reading based on the rules and current time.
    Returns a dict of actions (possibly empty).
    """
    current_time = datetime.now().strftime('%H:%M')
    active_rules = rules.get(active_rule_set, {})
    for entry in active_rules.get(sensor_name, []):
        minv = entry.get('min', float('-inf'))
        maxv = entry.get('max', float('inf'))
        time_range = entry.get('time', '')
        if minv <= value <= maxv and is_time_in_range(time_range, current_time):
            return entry.get('actions', {}) or {}
    return {}

def update_actions(data, rules, active_rule_set):
    """
    Update only the 'action' section of the data dict, merging new actions
    without removing others.
    """
    current_actions = data.get('action', {}).copy()
    sensors = data.get('sensors', {})

    for sensor_name, sensor_value in sensors.items():
        new_actions = get_actions_for(sensor_name, sensor_value, rules, active_rule_set)
        # Merge: overwrite existing keys, leave others intact
        for key, val in new_actions.items():
            current_actions[key] = val

    data['action'] = current_actions
    return data

def background_task():
    while True:
        try:
            config = load_json(CONFIG_FILE, CONFIG_LOCK_FILE)
            active_rule_set = config.get('active_rule_set', 'fixed_rule')
            rules = load_json(RULES_FILE)
            data = load_json(DATA_FILE, LOCK_FILE)

            updated = update_actions(data, rules, active_rule_set)
            save_json(DATA_FILE, updated, LOCK_FILE)

            # Save status to status.json with separated sensor and action data
            status_message = (
                f"Updated {time.strftime('%H:%M:%S')}\n"
                f"Sensors: Light: {updated['sensors']['light_level']}, Temp: {updated['sensors']['temperature']}°C, Humidity: {updated['sensors']['humidity']}%\n"
                f"Actions: Fan: {updated['action']['fan'].capitalize()}, Speed: {updated['action']['fan_speed']}%, Light: {updated['action']['light'].capitalize()}, Brightness: {updated['action']['set_brightness']}%\n"
                f"Active Rule Set: {active_rule_set}"
            )
            with FileLock(STATUS_LOCK_FILE):
                with open(STATUS_FILE, 'w') as f:
                    json.dump({"status": status_message}, f)
        except Exception as e:
            # Save error status to status.json
            status_message = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error during update: {e}"
            with FileLock(STATUS_LOCK_FILE):
                with open(STATUS_FILE, 'w') as f:
                    json.dump({"status": status_message}, f)

        time.sleep(UPDATE_INTERVAL)