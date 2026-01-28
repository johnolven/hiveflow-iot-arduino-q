/*
 * ============================================================
 * ARDUINO UNO Q - MCU SKETCH (STM32U585)
 * ============================================================
 * 
 * Author: John Olven
 * Project: HiveFlow IoT Demo
 * 
 * This sketch runs on the STM32 microcontroller of the UNO Q.
 * It reads HW-498 and HW-487 sensors and sends data to the MPU
 * via the Bridge RPC.
 * 
 * Use with: Arduino App Lab
 * 
 * Components:
 *   - Arduino UNO Q (Qualcomm Dragonwing QRB2210 + STM32U585)
 *   - HW-498 (Thermistor temperature sensor)
 *   - HW-487 (Photo interrupter sensor)
 *   - Built-in 8x13 LED Matrix
 *   - Built-in RGB LEDs
 * 
 * ============================================================
 */

#include <Arduino.h>
#include "Arduino_LED_Matrix.h"  // For built-in LED matrix

// ==================== PIN CONFIGURATION ====================
#define TEMP_SENSOR_PIN A0    // HW-498 Thermistor (Analog)
#define PHOTO_SENSOR_PIN 2    // HW-487 Photo Interrupter (Digital)

// Built-in RGB LEDs on UNO Q (controlled by MCU)
// LED_BUILTIN is already defined

// ==================== SETTINGS ====================
const float TEMP_THRESHOLD = 30.0;           // Temperature threshold in °C
const unsigned long READ_INTERVAL = 1000;    // 1 second

// ==================== OBJECTS ====================
ArduinoLEDMatrix matrix;

// ==================== VARIABLES ====================
unsigned long lastReading = 0;
float temperature = 0;
bool objectDetected = false;
bool alertActive = false;

// Frame for LED matrix (8x12)
uint8_t frame[8][12] = {0};

// ==================== FUNCTIONS ====================

// Convert analog reading to temperature (NTC thermistor)
float readTemperature() {
  int rawADC = analogRead(TEMP_SENSOR_PIN);
  
  // Formula for NTC thermistor (simplified Steinhart-Hart)
  // Adjust these values according to your specific thermistor
  float resistance = (1023.0 / rawADC - 1.0) * 10000.0;  // 10K pull-up resistor
  float tempK = 1.0 / (1.0/298.15 + (1.0/3950.0) * log(resistance/10000.0));
  float tempC = tempK - 273.15;
  
  return tempC;
}

// Read photo interrupter sensor
bool readPhotoSensor() {
  // HIGH = light blocked (object present)
  // LOW = light passing (no object)
  return digitalRead(PHOTO_SENSOR_PIN) == HIGH;
}

// Display pattern on LED matrix based on state
void updateLEDMatrix() {
  // Clear frame
  for (int y = 0; y < 8; y++) {
    for (int x = 0; x < 12; x++) {
      frame[y][x] = 0;
    }
  }
  
  if (alertActive) {
    // Alert pattern: X
    frame[0][0] = 1; frame[0][11] = 1;
    frame[1][1] = 1; frame[1][10] = 1;
    frame[2][2] = 1; frame[2][9] = 1;
    frame[3][3] = 1; frame[3][8] = 1;
    frame[4][4] = 1; frame[4][7] = 1;
    frame[5][5] = 1; frame[5][6] = 1;
    frame[6][4] = 1; frame[6][7] = 1;
    frame[7][3] = 1; frame[7][8] = 1;
  } else if (objectDetected) {
    // Object detected pattern: square
    for (int x = 2; x < 10; x++) {
      frame[1][x] = 1;
      frame[6][x] = 1;
    }
    for (int y = 1; y < 7; y++) {
      frame[y][2] = 1;
      frame[y][9] = 1;
    }
  } else {
    // Normal pattern: check mark
    frame[4][2] = 1;
    frame[5][3] = 1;
    frame[6][4] = 1;
    frame[5][5] = 1;
    frame[4][6] = 1;
    frame[3][7] = 1;
    frame[2][8] = 1;
    frame[1][9] = 1;
  }
  
  matrix.renderBitmap(frame, 8, 12);
}

// Control built-in LED based on temperature
void updateStatusLED() {
  if (alertActive) {
    // Blink on alert
    static unsigned long lastBlink = 0;
    static bool ledOn = false;
    
    if (millis() - lastBlink > 300) {
      lastBlink = millis();
      ledOn = !ledOn;
      digitalWrite(LED_BUILTIN, ledOn ? HIGH : LOW);
    }
  } else {
    digitalWrite(LED_BUILTIN, HIGH);  // LED on = normal
  }
}

// ==================== SETUP ====================
void setup() {
  // Start serial communication (for debug and Bridge)
  Serial.begin(115200);
  Serial.println("=== Arduino UNO Q - MCU ===");
  Serial.println("Starting sensors...");
  
  // Configure pins
  pinMode(TEMP_SENSOR_PIN, INPUT);
  pinMode(PHOTO_SENSOR_PIN, INPUT);
  pinMode(LED_BUILTIN, OUTPUT);
  
  // Start LED matrix
  matrix.begin();
  
  // Show startup pattern
  for (int y = 0; y < 8; y++) {
    for (int x = 0; x < 12; x++) {
      frame[y][x] = 1;
    }
  }
  matrix.renderBitmap(frame, 8, 12);
  delay(500);
  
  // Clear
  for (int y = 0; y < 8; y++) {
    for (int x = 0; x < 12; x++) {
      frame[y][x] = 0;
    }
  }
  matrix.renderBitmap(frame, 8, 12);
  
  Serial.println("System ready!");
  Serial.print("Temperature threshold: ");
  Serial.print(TEMP_THRESHOLD);
  Serial.println(" C");
}

// ==================== LOOP ====================
void loop() {
  unsigned long now = millis();
  
  if (now - lastReading >= READ_INTERVAL) {
    lastReading = now;
    
    // Read sensors
    temperature = readTemperature();
    objectDetected = readPhotoSensor();
    
    // Evaluate alert
    alertActive = (temperature >= TEMP_THRESHOLD);
    
    // Update displays
    updateLEDMatrix();
    
    // Send data via Serial (MPU reads via Bridge)
    // JSON format for easy parsing in Python
    Serial.print("{\"temperature\":");
    Serial.print(temperature, 2);
    Serial.print(",\"object_detected\":");
    Serial.print(objectDetected ? "true" : "false");
    Serial.print(",\"alert\":");
    Serial.print(alertActive ? "true" : "false");
    Serial.print(",\"threshold\":");
    Serial.print(TEMP_THRESHOLD, 1);
    Serial.println("}");
  }
  
  // Update status LED continuously
  updateStatusLED();
}
