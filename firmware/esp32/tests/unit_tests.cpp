/**
 * Unit Tests for ESP32 Mirror Body Firmware
 * Run with: platformio test -e esp32s3_test
 */

#include <Arduino.h>
#include <unity.h>
#include "led_controller.h"
#include "motor_controller.h"
#include "serial_protocol.h"

// ============= LED CONTROLLER TESTS =============

void test_led_init() {
    LEDController led;
    led.init();
    TEST_ASSERT_TRUE(led.is_initialized());
    TEST_ASSERT_EQUAL(2048, led.get_total_leds());
}

void test_led_set_pixel() {
    LEDController led;
    led.init();
    
    led.set_pixel(0, 255, 0, 0);
    TEST_ASSERT_EQUAL(255, led.get_pixel_r(0));
    TEST_ASSERT_EQUAL(0, led.get_pixel_g(0));
    TEST_ASSERT_EQUAL(0, led.get_pixel_b(0));
    
    led.set_pixel(100, 0, 255, 128);
    TEST_ASSERT_EQUAL(0, led.get_pixel_r(100));
    TEST_ASSERT_EQUAL(255, led.get_pixel_g(100));
    TEST_ASSERT_EQUAL(128, led.get_pixel_b(100));
}

void test_led_fill() {
    LEDController led;
    led.init();
    
    led.fill(255, 128, 64);
    
    for (int i = 0; i < 2048; i++) {
        TEST_ASSERT_EQUAL(255, led.get_pixel_r(i));
        TEST_ASSERT_EQUAL(128, led.get_pixel_g(i));
        TEST_ASSERT_EQUAL(64, led.get_pixel_b(i));
    }
}

void test_led_clear() {
    LEDController led;
    led.init();
    
    led.fill(255, 255, 255);
    led.clear();
    
    for (int i = 0; i < 2048; i++) {
        TEST_ASSERT_EQUAL(0, led.get_pixel_r(i));
        TEST_ASSERT_EQUAL(0, led.get_pixel_g(i));
        TEST_ASSERT_EQUAL(0, led.get_pixel_b(i));
    }
}

void test_led_brightness_range() {
    LEDController led;
    led.init();
    
    for (int b = 0; b <= 255; b += 51) {
        led.set_brightness(b);
        TEST_ASSERT_EQUAL(b, led.get_brightness());
    }
}

void test_led_gradient() {
    LEDController led;
    led.init();
    
    led.create_gradient(0, 2048, 255, 0, 0, 0, 255, 0);
    
    TEST_ASSERT_EQUAL(255, led.get_pixel_r(0));
    TEST_ASSERT_EQUAL(0, led.get_pixel_g(0));
    
    TEST_ASSERT_EQUAL(0, led.get_pixel_r(2047));
    TEST_ASSERT_EQUAL(255, led.get_pixel_g(2047));
}

void test_led_bounds() {
    LEDController led;
    led.init();
    
    led.set_pixel(-1, 255, 0, 0);
    led.set_pixel(9999, 255, 0, 0);
    
    led.set_pixel(0, 0, 255, 0);
    TEST_ASSERT_EQUAL(0, led.get_pixel_r(0));
    TEST_ASSERT_EQUAL(255, led.get_pixel_g(0));
}

// ============= MOTOR CONTROLLER TESTS =============

void test_motor_init() {
    MotorController motor;
    motor.init();
    TEST_ASSERT_TRUE(motor.is_initialized());
    TEST_ASSERT_EQUAL(64, motor.get_num_servos());
}

void test_motor_set_angle() {
    MotorController motor;
    motor.init();
    
    motor.set_angle(0, 90);
    TEST_ASSERT_EQUAL(90, motor.get_angle(0));
    
    motor.set_angle(63, 45);
    TEST_ASSERT_EQUAL(45, motor.get_angle(63));
}

void test_motor_angle_limits() {
    MotorController motor;
    motor.init();
    
    motor.set_angle(0, 0);
    TEST_ASSERT_EQUAL(0, motor.get_angle(0));
    
    motor.set_angle(0, 180);
    TEST_ASSERT_EQUAL(180, motor.get_angle(0));
    
    motor.set_angle(0, -10);
    TEST_ASSERT_EQUAL(0, motor.get_angle(0));
    
    motor.set_angle(0, 200);
    TEST_ASSERT_EQUAL(180, motor.get_angle(0));
}

void test_motor_all_servos() {
    MotorController motor;
    motor.init();
    
    motor.set_all_servos(90);
    
    for (int i = 0; i < 64; i++) {
        TEST_ASSERT_EQUAL(90, motor.get_angle(i));
    }
}

void test_motor_calibration() {
    MotorController motor;
    motor.init();
    
    motor.calibrate();
    
    for (int i = 0; i < 64; i++) {
        TEST_ASSERT_EQUAL(90, motor.get_angle(i));
    }
}

// ============= SERIAL PROTOCOL TESTS =============

void test_protocol_parse_led_command() {
    SerialProtocol protocol;
    
    const char* cmd = "LED:0,255,0,0";
    Command parsed = protocol.parse(cmd);
    
    TEST_ASSERT_EQUAL(CMD_LED, parsed.type);
    TEST_ASSERT_EQUAL(0, parsed.led_index);
    TEST_ASSERT_EQUAL(255, parsed.r);
    TEST_ASSERT_EQUAL(0, parsed.g);
    TEST_ASSERT_EQUAL(0, parsed.b);
}

void test_protocol_parse_motor_command() {
    SerialProtocol protocol;
    
    const char* cmd = "MOTOR:0,90";
    Command parsed = protocol.parse(cmd);
    
    TEST_ASSERT_EQUAL(CMD_MOTOR, parsed.type);
    TEST_ASSERT_EQUAL(0, parsed.motor_index);
    TEST_ASSERT_EQUAL(90, parsed.angle);
}

void test_protocol_parse_invalid_command() {
    SerialProtocol protocol;
    
    const char* cmd = "INVALID:XYZ";
    Command parsed = protocol.parse(cmd);
    
    TEST_ASSERT_EQUAL(CMD_ERROR, parsed.type);
}

// ============= RUN ALL TESTS =============

void setup() {
    delay(2000);
    Serial.begin(115200);
    
    UNITY_BEGIN();
    
    RUN_TEST(test_led_init);
    RUN_TEST(test_led_set_pixel);
    RUN_TEST(test_led_fill);
    RUN_TEST(test_led_clear);
    RUN_TEST(test_led_brightness_range);
    RUN_TEST(test_led_gradient);
    RUN_TEST(test_led_bounds);
    
    RUN_TEST(test_motor_init);
    RUN_TEST(test_motor_set_angle);
    RUN_TEST(test_motor_angle_limits);
    RUN_TEST(test_motor_all_servos);
    RUN_TEST(test_motor_calibration);
    
    RUN_TEST(test_protocol_parse_led_command);
    RUN_TEST(test_protocol_parse_motor_command);
    RUN_TEST(test_protocol_parse_invalid_command);
    
    UNITY_END();
}

void loop() {
    // Nothing here
}
