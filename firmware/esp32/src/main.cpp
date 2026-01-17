#include <Arduino.h>
#include <FastLED.h>

namespace {

constexpr uint8_t LED_PIN_LEFT = 5;
constexpr uint8_t LED_PIN_RIGHT = 18;
constexpr uint32_t BAUD_RATE = 460800;
constexpr uint16_t MATRIX_WIDTH = 32;
constexpr uint16_t MATRIX_HEIGHT = 64;
constexpr uint16_t NUM_LEDS = MATRIX_WIDTH * MATRIX_HEIGHT;
constexpr uint16_t LEDS_PER_STRIP = NUM_LEDS / 2;
constexpr uint8_t GLOBAL_BRIGHTNESS = 200;
constexpr uint32_t FRAME_TIMEOUT_MS = 2000;

constexpr uint8_t PKT_HEADER_0 = 0xAA;
constexpr uint8_t PKT_HEADER_1 = 0xBB;
constexpr uint8_t PKT_TYPE_LED = 0x01;
constexpr uint16_t PACKET_LED_SIZE = 3 + NUM_LEDS;

CRGB ledsLeft[LEDS_PER_STRIP];
CRGB ledsRight[LEDS_PER_STRIP];

uint8_t packetBuffer[PACKET_LED_SIZE];
uint16_t packetIndex = 0;
bool packetActive = false;
uint32_t lastFrameMs = 0;

void resetPacket() {
  packetIndex = 0;
  packetActive = false;
}

void applyLedPayload(const uint8_t *payload) {
  for (uint16_t i = 0; i < NUM_LEDS; ++i) {
    const uint8_t value = payload[i];
    if (i < LEDS_PER_STRIP) {
      ledsLeft[i] = CRGB(value, value, value);
    } else {
      ledsRight[i - LEDS_PER_STRIP] = CRGB(value, value, value);
    }
  }
  FastLED.show();
  lastFrameMs = millis();
}

void clearIfStale() {
  if (lastFrameMs == 0) {
    return;
  }
  if (millis() - lastFrameMs > FRAME_TIMEOUT_MS) {
    FastLED.clear(true);
    lastFrameMs = 0;
  }
}

void processIncomingByte(uint8_t inByte) {
  if (packetIndex == 0) {
    if (inByte == PKT_HEADER_0) {
      packetBuffer[packetIndex++] = inByte;
      packetActive = true;
    }
    return;
  }

  if (packetIndex == 1) {
    if (inByte == PKT_HEADER_1) {
      packetBuffer[packetIndex++] = inByte;
    } else {
      resetPacket();
    }
    return;
  }

  if (packetIndex == 2) {
    if (inByte == PKT_TYPE_LED) {
      packetBuffer[packetIndex++] = inByte;
    } else {
      resetPacket();
    }
    return;
  }

  if (!packetActive) {
    resetPacket();
    return;
  }

  if (packetIndex >= PACKET_LED_SIZE) {
    resetPacket();
    return;
  }

  packetBuffer[packetIndex++] = inByte;

  if (packetIndex == PACKET_LED_SIZE) {
    applyLedPayload(&packetBuffer[3]);
    resetPacket();
  }
}

} // namespace

void setup() {
  delay(150);
  Serial.begin(BAUD_RATE);
  Serial.setTimeout(1);
  Serial.println();
  Serial.println("=== MIRROR LED BRIDGE ===");
  Serial.println("Mode: LED_STREAM_ONLY");
  Serial.println("READY");

  FastLED.addLeds<WS2812B, LED_PIN_LEFT, GRB>(ledsLeft, LEDS_PER_STRIP);
  FastLED.addLeds<WS2812B, LED_PIN_RIGHT, GRB>(ledsRight, LEDS_PER_STRIP);
  FastLED.setBrightness(GLOBAL_BRIGHTNESS);
  FastLED.setDither(false);
  FastLED.clear(true);
}

void loop() {
  while (Serial.available() > 0) {
    const uint8_t inByte = static_cast<uint8_t>(Serial.read());
    processIncomingByte(inByte);
  }

  if (Serial.available() > PACKET_LED_SIZE * 2) {
    while (Serial.available() > 0) {
      static_cast<void>(Serial.read());
    }
    resetPacket();
  }

  clearIfStale();
  delay(1);
}
