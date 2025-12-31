/**
 * LED Controller for ESP32-S3
 * Controls 2048 WS2812B LEDs (8 panels of 16x16)
 */

#ifndef LED_CONTROLLER_H
#define LED_CONTROLLER_H

#include "driver/rmt.h"
#include "driver/gpio.h"
#include "esp_heap_caps.h"

#define LED_COUNT 2048
#define LED_PIN 12

class LEDController {
private:
    bool initialized = false;
    uint8_t* led_buffer;
    uint8_t brightness = 255;
    rmt_channel_t rmt_channel;
    
public:
    LEDController() {
        led_buffer = (uint8_t*)heap_caps_malloc(LED_COUNT * 3, MALLOC_CAP_8BIT);
        if (led_buffer) {
            memset(led_buffer, 0, LED_COUNT * 3);
        }
    }
    
    ~LEDController() {
        if (led_buffer) {
            free(led_buffer);
        }
    }
    
    void init() {
        if (initialized) return;
        
        rmt_config_t config;
        config.rmt_mode = RMT_MODE_TX;
        config.channel = RMT_CHANNEL_0;
        config.gpio_num = (gpio_num_t)LED_PIN;
        config.mem_block_num = 8;
        config.clk_div = 2;
        config.tx_config.loop_en = false;
        config.tx_config.carrier_en = false;
        config.tx_config.idle_output_en = true;
        config.tx_config.idle_level = 0;
        
        esp_err_t err = rmt_config(&config);
        err |= rmt_driver_install(config.channel, 0, 0);
        
        if (err == ESP_OK) {
            initialized = true;
            Serial.println("[LEDController] Initialized");
        } else {
            Serial.println("[LEDController] Failed to initialize!");
        }
    }
    
    bool is_initialized() {
        return initialized;
    }
    
    int get_total_leds() {
        return LED_COUNT;
    }
    
    void set_pixel(int index, uint8_t r, uint8_t g, uint8_t b) {
        if (index < 0 || index >= LED_COUNT || !led_buffer) return;
        
        int pos = index * 3;
        led_buffer[pos] = r;
        led_buffer[pos + 1] = g;
        led_buffer[pos + 2] = b;
    }
    
    uint8_t get_pixel_r(int index) {
        if (index < 0 || index >= LED_COUNT || !led_buffer) return 0;
        return led_buffer[index * 3];
    }
    
    uint8_t get_pixel_g(int index) {
        if (index < 0 || index >= LED_COUNT || !led_buffer) return 0;
        return led_buffer[index * 3 + 1];
    }
    
    uint8_t get_pixel_b(int index) {
        if (index < 0 || index >= LED_COUNT || !led_buffer) return 0;
        return led_buffer[index * 3 + 2];
    }
    
    void fill(uint8_t r, uint8_t g, uint8_t b) {
        if (!led_buffer) return;
        for (int i = 0; i < LED_COUNT; i++) {
            set_pixel(i, r, g, b);
        }
    }
    
    void clear() {
        fill(0, 0, 0);
    }
    
    void set_brightness(uint8_t b) {
        brightness = b;
    }
    
    uint8_t get_brightness() {
        return brightness;
    }
    
    void create_gradient(int start, int count, uint8_t r1, uint8_t g1, uint8_t b1, uint8_t r2, uint8_t g2, uint8_t b2) {
        for (int i = 0; i < count; i++) {
            float t = (float)i / count;
            uint8_t r = r1 + (r2 - r1) * t;
            uint8_t g = g1 + (g2 - g1) * t;
            uint8_t b = b1 + (b2 - b1) * t;
            set_pixel(start + i, r, g, b);
        }
    }
    
    void create_rainbow() {
        for (int i = 0; i < LED_COUNT; i++) {
            uint8_t hue = (i * 256 / LED_COUNT) % 256;
            // Simple HSV to RGB conversion
            set_pixel(i, hue, 255 - hue, 0);
        }
    }
    
    void create_fire() {
        for (int i = 0; i < LED_COUNT; i++) {
            int flicker = random(0, 50);
            uint8_t r = 255 - flicker;
            uint8_t g = random(0, 100);
            uint8_t b = 0;
            set_pixel(i, r, g, b);
        }
    }
    
    void create_wave() {
        for (int i = 0; i < LED_COUNT; i++) {
            float wave = sin(i * 0.05 + millis() * 0.002) * 0.5 + 0.5;
            uint8_t r = 255 * wave;
            uint8_t g = 128 * wave;
            uint8_t b = 255 * wave;
            set_pixel(i, r, g, b);
        }
    }
    
    void test_pattern() {
        fill(255, 0, 0);
        delay(500);
        fill(0, 255, 0);
        delay(500);
        fill(0, 0, 255);
        delay(500);
        clear();
    }
    
    void update() {
        if (!initialized || !led_buffer) return;
        
        // Send to RMT (this is simplified - actual implementation needs RMT pulse data)
        rmt_write_sample(rmt_channel, led_buffer, LED_COUNT * 3, false);
    }
};

#endif // LED_CONTROLLER_H
