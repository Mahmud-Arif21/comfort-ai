import paho.mqtt.client as mqtt
import json
import time
import os
import re
from filelock import FileLock

# --- MQTT Broker Configuration ---
MQTT_BROKER = "172.16.16.54"
MQTT_PORT = 1883
MQTT_CLIENT_ID = "paho_continuous_publisher"
MQTT_CONNECTION_TIMEOUT = 60
MAX_RETRIES = 3
PUBLISH_INTERVAL = 1  # 1 second interval

# --- File Configuration ---
JSON_FILE = os.path.join(os.path.dirname(__file__), "data.json")
JSON_LOCK_FILE = JSON_FILE + '.lock'
MQTT_STATUS_FILE = os.path.join(os.path.dirname(__file__), "mqtt_status.json")
MQTT_STATUS_LOCK_FILE = MQTT_STATUS_FILE + '.lock'

# --- Utility Functions ---
def update_status(message):
    try:
        with FileLock(MQTT_STATUS_LOCK_FILE):
            with open(MQTT_STATUS_FILE, 'w') as f:
                json.dump({
                    "status": f"{message} | Last update: {time.strftime('%H:%M:%S')}"
                }, f)
    except Exception as e:
        print(f"Error updating MQTT status: {e}")

def load_actions():
    try:
        with FileLock(JSON_LOCK_FILE):
            with open(JSON_FILE, 'r') as f:
                data = json.load(f)
                return data.get("action", {})
    except Exception as e:
        update_status(f"Error loading actions: {str(e)}")
        return {}

def validate_topic(topic):
    return bool(re.match(r"^[a-zA-Z0-9_\/-]+$", topic))

# --- MQTT Publisher Background Task (Like update.py) ---
def mqtt_background_task():
    """
    Background task function that runs continuously, just like background_task in update.py
    This function will be called by app.py as a background thread
    """
    client = None
    last_actions = {}
    
    # Initialize MQTT client
    try:
        client = mqtt.Client(client_id=MQTT_CLIENT_ID)
        
        # Set up callbacks
        def on_connect(client, userdata, flags, rc):
            update_status(f"Connected: Code {rc}")
        
        def on_disconnect(client, userdata, rc):
            update_status(f"Disconnected: Code {rc}")
        
        def on_publish(client, userdata, mid):
            pass  # Status handled in main loop
        
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_publish = on_publish
        
        # Initial connection
        client.connect(MQTT_BROKER, MQTT_PORT, MQTT_CONNECTION_TIMEOUT)
        client.loop_start()
        update_status("MQTT Publisher initialized")
        
    except Exception as e:
        update_status(f"Initial connection failed: {str(e)}")
        return
    
    # Main publishing loop (similar to update.py's while loop)
    while True:
        try:
            # Check connection
            if not client.is_connected():
                update_status("Attempting reconnection...")
                try:
                    client.reconnect()
                    time.sleep(1)
                except Exception as e:
                    update_status(f"Reconnection failed: {str(e)}")
                    time.sleep(PUBLISH_INTERVAL)
                    continue
            
            # Load current actions
            current_actions = load_actions()
            
            # Only publish if actions changed
            if current_actions != last_actions:
                published_count = 0
                for topic, payload in current_actions.items():
                    if validate_topic(topic):
                        try:
                            json_payload = json.dumps(payload)
                            result = client.publish(topic, json_payload, qos=1)
                            if result.rc == 0:
                                published_count += 1
                            else:
                                update_status(f"Publish failed for {topic}: Code {result.rc}")
                        except Exception as e:
                            update_status(f"Publish error on {topic}: {str(e)}")
                    else:
                        update_status(f"Invalid topic: {topic}")
                
                if published_count > 0:
                    update_status(f"Published {published_count} topics successfully")
                
                last_actions = current_actions.copy()
            else:
                # Update status even when no changes (to show it's alive)
                update_status("MQTT Publisher running - No changes to publish")
            
            time.sleep(PUBLISH_INTERVAL)
            
        except KeyboardInterrupt:
            update_status("Publisher stopped by user")
            break
        except Exception as e:
            update_status(f"Critical error: {str(e)}")
            time.sleep(5)
    
    # Cleanup
    if client:
        client.loop_stop()
        client.disconnect()
        update_status("Publisher shutdown complete")

# --- For standalone execution (optional) ---
if __name__ == "__main__":
    mqtt_background_task()