/*
 * LED Panel Test Firmware - STANDALONE TEST FILE
 * DO NOT modify main firmware - this is for LED panel testing only
 *
 * Upload this to test LED panels separately from main system
 * To upload: python -m platformio run --target upload --upload-port COM5
 */

#include <FastLED.h>

// LED Configuration
#define NUM_LEDS 2048
#define LEDS_PER_PIN 1024
#define PIN_LEFT 5
#define PIN_RIGHT 18

#define TOTAL_W 32
#define TOTAL_H 64
#define PANEL_W 16
#define PANEL_H 16

// FastLED arrays
CRGB leds_left[LEDS_PER_PIN];
CRGB leds_right[LEDS_PER_PIN];

// Serial packet
#define PKT_TYPE_LED 0x01
#define PACKET_LED_SIZE 2051
uint8_t packetBuffer[PACKET_LED_SIZE];
uint16_t packetIndex = 0;
uint8_t currentPacketType = 0;

// Test mode
uint8_t testMode = 0; // 0=serial, 1=auto test patterns
unsigned long lastTestChange = 0;

// LED mapping function (with XY inversion)
inline uint16_t XY(uint8_t x, uint8_t y) {
  uint8_t cx = TOTAL_W - 1 - x;
  uint8_t cy = TOTAL_H - 1 - y;

  uint8_t panelRow = cy / PANEL_H;
  uint8_t localX = cx % PANEL_W;
  uint8_t localY = cy % PANEL_H;

  uint16_t localIdx;
  if (localY % 2 == 0) {
    localIdx = (localY * PANEL_W) + localX;
  } else {
    localIdx = (localY * PANEL_W) + (PANEL_W - 1 - localX);
  }

  uint16_t baseIdx = panelRow * 256;

  if (cx < 16) {
    return baseIdx + localIdx;
  } else {
    return LEDS_PER_PIN + baseIdx + localIdx;
  }
}

void setup() {
  Serial.begin(460800);

  // Initialize FastLED
  FastLED.addLeds<WS2812B, PIN_LEFT, GRB>(leds_left, LEDS_PER_PIN);
  FastLED.addLeds<WS2812B, PIN_RIGHT, GRB>(leds_right, LEDS_PER_PIN);
  FastLED.setBrightness(255);
  FastLED.clear();
  FastLED.show();

  Serial.println("LED Panel Test Firmware Ready");
  Serial.println("Commands:");
  Serial.println("  0-9: Run auto test pattern");
  Serial.println("  s: Switch to serial mode");
  Serial.println("  c: Clear all LEDs");
}

void loop() {
  // Check for serial command
  if (Serial.available() > 0) {
    char cmd = Serial.read();

    if (cmd == 's') {
      testMode = 0;
      Serial.println("Mode: Serial");
      return;
    } else if (cmd == 'c') {
      FastLED.clear();
      FastLED.show();
      Serial.println("Cleared");
      return;
    } else if (cmd >= '0' && cmd <= '9') {
      testMode = 1 + (cmd - '0');
      Serial.print("Auto Test: ");
      Serial.println(testMode - 1);
      runAutoTest(testMode - 1);
      return;
    }
  }

  // Serial packet mode
  if (testMode == 0) {
    processSerialPacket();
  }
  // Auto test modes run once when activated
}

void processSerialPacket() {
  while (Serial.available() > 0) {
    uint8_t inByte = Serial.read();

    if (packetIndex == 0 && inByte == 0xAA) {
      packetBuffer[packetIndex++] = inByte;
    } else if (packetIndex == 1) {
      if (inByte == 0xBB) {
        packetBuffer[packetIndex++] = inByte;
      } else {
        packetIndex = 0;
      }
    } else if (packetIndex == 2) {
      if (inByte == PKT_TYPE_LED) {
        currentPacketType = inByte;
        packetBuffer[packetIndex++] = inByte;
      } else {
        packetIndex = 0;
        currentPacketType = 0;
      }
    } else if (packetIndex > 2) {
      if (packetIndex >= PACKET_LED_SIZE) {
        packetIndex = 0;
        currentPacketType = 0;
        continue;
      }

      packetBuffer[packetIndex++] = inByte;

      if (currentPacketType == PKT_TYPE_LED && packetIndex >= PACKET_LED_SIZE) {
        displayLEDPacket();
        packetIndex = 0;
        currentPacketType = 0;
      }
    }
  }
}

void displayLEDPacket() {
  if (packetBuffer[0] == 0xAA && packetBuffer[1] == 0xBB &&
      packetBuffer[2] == PKT_TYPE_LED) {
    uint8_t *data = &packetBuffer[3];

    for (uint8_t y = 0; y < TOTAL_H; y++) {
      for (uint8_t x = 0; x < TOTAL_W; x++) {
        uint16_t dataIdx = (y * TOTAL_W) + x;
        uint8_t value = data[dataIdx];
        uint16_t ledIdx = XY(x, y);

        if (value > 10) {
          if (ledIdx < LEDS_PER_PIN) {
            leds_left[ledIdx] = CRGB(value, value, value);
          } else {
            leds_right[ledIdx - LEDS_PER_PIN] = CRGB(value, value, value);
          }
        } else {
          if (ledIdx < LEDS_PER_PIN) {
            leds_left[ledIdx] = CRGB::Black;
          } else {
            leds_right[ledIdx - LEDS_PER_PIN] = CRGB::Black;
          }
        }
      }
    }

    FastLED.show();
  }
}

void runAutoTest(uint8_t testNum) {
  FastLED.clear();

  switch (testNum) {
  case 0:
    testAllWhite();
    break;
  case 1:
    testBrightness();
    break;
  case 2:
    testCheckerboard();
    break;
  case 3:
    testIndividualPanels();
    break;
  case 4:
    testVerticalBars();
    break;
  case 5:
    testHorizontalBars();
    break;
  default:
    Serial.println("Unknown test");
    return;
  }

  FastLED.show();
}

void testAllWhite() {
  Serial.println("Test: All White");
  for (int i = 0; i < LEDS_PER_PIN; i++) {
    leds_left[i] = CRGB::White;
    leds_right[i] = CRGB::White;
  }
}

void testBrightness() {
  Serial.println("Test: Brightness Levels");
  uint8_t brightness[] = {30, 60, 90, 120, 150, 180, 210, 255};

  for (uint8_t panel = 0; panel < 8; panel++) {
    uint8_t row = panel / 2;
    uint8_t col = panel % 2;
    uint8_t bright = brightness[panel];

    for (uint8_t py = 0; py < 16; py++) {
      for (uint8_t px = 0; px < 16; px++) {
        uint8_t x = col * 16 + px;
        uint8_t y = row * 16 + py;
        uint16_t idx = XY(x, y);

        if (idx < LEDS_PER_PIN) {
          leds_left[idx] = CRGB(bright, bright, bright);
        } else {
          leds_right[idx - LEDS_PER_PIN] = CRGB(bright, bright, bright);
        }
      }
    }
  }
}

void testCheckerboard() {
  Serial.println("Test: Checkerboard");
  for (uint8_t y = 0; y < TOTAL_H; y++) {
    for (uint8_t x = 0; x < TOTAL_W; x++) {
      if (((y / 4) + (x / 4)) % 2 == 0) {
        uint16_t idx = XY(x, y);
        if (idx < LEDS_PER_PIN) {
          leds_left[idx] = CRGB::White;
        } else {
          leds_right[idx - LEDS_PER_PIN] = CRGB::White;
        }
      }
    }
  }
}

void testIndividualPanels() {
  Serial.println("Test: Individual Panels (cycling)");
  for (uint8_t panel = 0; panel < 8; panel++) {
    FastLED.clear();

    uint8_t row = panel / 2;
    uint8_t col = panel % 2;

    for (uint8_t py = 0; py < 16; py++) {
      for (uint8_t px = 0; px < 16; px++) {
        uint8_t x = col * 16 + px;
        uint8_t y = row * 16 + py;
        uint16_t idx = XY(x, y);

        if (idx < LEDS_PER_PIN) {
          leds_left[idx] = CRGB::White;
        } else {
          leds_right[idx - LEDS_PER_PIN] = CRGB::White;
        }
      }
    }

    FastLED.show();
    Serial.print("Panel ");
    Serial.println(panel + 1);
    delay(1000);
  }
}

void testVerticalBars() {
  Serial.println("Test: Vertical Bars");
  for (uint8_t y = 0; y < TOTAL_H; y++) {
    for (uint8_t x = 0; x < TOTAL_W; x++) {
      if (x % 2 == 0) {
        uint16_t idx = XY(x, y);
        if (idx < LEDS_PER_PIN) {
          leds_left[idx] = CRGB::White;
        } else {
          leds_right[idx - LEDS_PER_PIN] = CRGB::White;
        }
      }
    }
  }
}

void testHorizontalBars() {
  Serial.println("Test: Horizontal Bars");
  for (uint8_t y = 0; y < TOTAL_H; y++) {
    for (uint8_t x = 0; x < TOTAL_W; x++) {
      if (y % 2 == 0) {
        uint16_t idx = XY(x, y);
        if (idx < LEDS_PER_PIN) {
          leds_left[idx] = CRGB::White;
        } else {
          leds_right[idx - LEDS_PER_PIN] = CRGB::White;
        }
      }
    }
  }
}
