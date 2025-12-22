#include <Arduino.h>

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("Hello World! ESP32-S3 is Alive.");
}

void loop() {
  Serial.println("Tick...");
  delay(1000);
}
