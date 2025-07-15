/*
 * Comfort AI ESP32 Subscriber
 * 
 * This sketch connects an ESP32 to a WiFi network and subscribes to an MQTT broker
 * to control a fan and a light based on messages received on specific topics.
 * 
 * ### Hardware Setup:
 * - **Light**: Connected to the built-in LED on pin 2 (adjust if your ESP32's built-in LED is on a different pin).
 * - **Fan**: For testing, connect an LED to pin 4 to simulate the fan.
 *   (In a real setup, connect a fan through a relay or appropriate driver, as ESP32 pins cannot directly power a fan.)
 * 
 * ### Prerequisites:
 * - Arduino IDE with ESP32 board support installed.
 * - PubSubClient library installed in Arduino IDE.
 * 
 * ### Setup Instructions:
 * 1. Install Arduino IDE from [arduino.cc](https://www.arduino.cc/en/software).
 * 2. Add ESP32 board support:
 *    - Go to **File > Preferences**, add `https://dl.espressif.com/dl/package_esp32_index.json` to "Additional Boards Manager URLs".
 *    - Go to **Tools > Board > Boards Manager**, search for "ESP32", and install.
 * 3. Install PubSubClient library:
 *    - Go to **Sketch > Include Library > Manage Libraries**, search for "PubSubClient", and install.
 * 4. Replace the placeholders below with your own values:
 *    - `ssid` and `password` with your WiFi network's SSID and password.
 *    - `mqtt_server` with your MQTT broker's IP address.
 * 5. Upload the code:
 *    - Open this sketch in Arduino IDE, select your ESP32 board under **Tools > Board**, connect via USB, and click **Upload**.
 * 
 * ### MQTT Broker Setup:
 * - Install Mosquitto on a device on your network (e.g., a computer or Raspberry Pi).
 * - Steps:
 *   1. Download Mosquitto from [mosquitto.org](https://mosquitto.org/download/).
 *   2. Install it following your OS instructions.
 *   3. Configure Mosquitto to listen on your device's IP and port 1883:
 *      - Edit `mosquitto.conf` and add:
 *        ```
 *        listener 1883 your_broker_ip
 *        allow_anonymous true
 *        ```
 *      - Replace `your_broker_ip` with the device's IP address.
 *      - Restart Mosquitto (e.g., `sudo systemctl restart mosquitto` on Linux).
 *   4. Verify it’s running (e.g., `netstat -tuln` on Linux to check your_broker_ip:1883).
 * - Ensure the broker is on the same network as the ESP32 or reachable via the specified IP.
 * 
 * ### Notes:
 * - If your MQTT broker requires authentication, set `mqtt_user` and `mqtt_password`.
 * - To find your broker’s IP: Windows (`ipconfig`), Linux/Mac (`ifconfig` or `ip addr`).
 * - Check WiFi and MQTT connection if the ESP32 fails to connect.
 */

#include <WiFi.h>
#include <PubSubClient.h>

// WiFi credentials - Replace with your network's SSID and password
const char* ssid = "your_wifi_ssid";  // e.g., "MyWiFiNetwork"
const char* password = "your_wifi_password";  // e.g., "MyPassword123"

// MQTT Broker settings - Replace with your MQTT broker's IP address
const char* mqtt_server = "your_mqtt_broker_ip";  // e.g., "192.168.1.100"
const int mqtt_port = 1883;  // Default MQTT port (change if your broker uses a different port)
const char* mqtt_user = "";  // Set if your broker requires authentication, e.g., "username"
const char* mqtt_password = "";  // Set if your broker requires authentication, e.g., "password"

// MQTT Topics
const char* fan_topic = "fan";
const char* light_topic = "light";

// Pin definitions
const int BUILTIN_LED_PIN = 2;  // ESP32 built-in LED pin for light (may vary on some boards)
const int FAN_PIN = 4;          // Digital pin for fan control (connect an LED for testing)

// WiFi and MQTT client objects
WiFiClient espClient;
PubSubClient client(espClient);

void setup() {
  Serial.begin(115200);
  
  // Add small delay for ESP32 stability
  delay(1000);
  
  // Initialize pins
  pinMode(BUILTIN_LED_PIN, OUTPUT);
  pinMode(FAN_PIN, OUTPUT);
  
  // Start with both devices off
  digitalWrite(BUILTIN_LED_PIN, LOW);
  digitalWrite(FAN_PIN, LOW);
  
  // Connect to WiFi
  setup_wifi();
  
  // Setup MQTT
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  
  Serial.println("System initialized");
}

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void callback(char* topic, byte* payload, unsigned int length) {
  // Convert payload to string
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  Serial.println(message);
  
  // Convert message to lowercase for comparison
  message.toLowerCase();
  
  // Remove quotes if present
  message.replace("\"", "");
  message.trim(); // Remove any whitespace
  
  // Handle light topic
  if (String(topic) == light_topic) {
    if (message == "on") {
      digitalWrite(BUILTIN_LED_PIN, HIGH);
      Serial.println("Light turned ON");
    } else if (message == "off") {
      digitalWrite(BUILTIN_LED_PIN, LOW);
      Serial.println("Light turned OFF");
    } else {
      Serial.println("Invalid light command. Use 'on' or 'off'");
    }
  }
  
  // Handle fan topic
  else if (String(topic) == fan_topic) {
    if (message == "on") {
      digitalWrite(FAN_PIN, HIGH);
      Serial.println("Fan turned ON");
    } else if (message == "off") {
      digitalWrite(FAN_PIN, LOW);
      Serial.println("Fan turned OFF");
    } else {
      Serial.println("Invalid fan command. Use 'on' or 'off'");
    }
  }
}

void reconnect() {
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    
    // Create a random client ID
    String clientId = "ESP32Client-";
    clientId += String(random(0xffff), HEX);
    
    // Attempt to connect
    if (client.connect(clientId.c_str(), mqtt_user, mqtt_password)) {
      Serial.println("connected");
      
      // Subscribe to topics
      client.subscribe(fan_topic);
      client.subscribe(light_topic);
      
      Serial.print("Subscribed to: ");
      Serial.println(fan_topic);
      Serial.print("Subscribed to: ");
      Serial.println(light_topic);
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  // Small delay to prevent overwhelming the system
  delay(100);
}
