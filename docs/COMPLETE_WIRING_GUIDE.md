# 🔧 Complete Wiring Guide - Mirror Body Simulation System

## Overview
This guide provides step-by-step wiring instructions for the complete Mirror Body system including ESP32, LED panels, and 64 servo motors.

---

## 📋 Table of Contents
1. [Power Distribution](#power-distribution)
2. [ESP32 to LED Panels](#esp32-to-led-panels)
3. [ESP32 to Motor Driver PCA9685](#esp32-to-motor-driver)
4. [Motor Driver to Servo Motors](#motor-driver-to-servo-motors)
5. [Wiring Diagram Summary](#wiring-diagram-summary)
6. [Safety Precautions](#safety-precautions)

---

## 🔌 Power Distribution

### Main Power Requirements
- **ESP32**: 5V (USB) or 5V DC adapter
- **LED Panels**: 5V, ~3A per panel (8 panels total = ~24A)
- **Servo Motors**: 5V or 6V, ~1A per motor (64 motors total = ~64A peak)

### Recommended Power Setup
```
[USB Power/Adapter 5V 3A] --> [ESP32]
[Power Supply 5V 30A+]    --> [LED Power Bus]
[Power Supply 5V/6V 70A+] --> [Motor Power Bus]
```

### Power Bus Wiring
1. **LED Power Bus**: Use a terminal block or PCB
   - Connect all LED panel VCC together to +5V
   - Connect all LED panel GND together to GND
   - **IMPORTANT**: Use thick wires (16 AWG or larger) for main power lines

2. **Motor Power Bus**: Use a terminal block
   - Connect all motor VCC together to +5V/6V
   - Connect all motor GND together to GND
   - **IMPORTANT**: Use thick wires (14 AWG or larger) for motor power

---

## 🔗 ESP32 to LED Panels

### ESP32-S3 Data Pins
```
ESP32 Pin 12  -->  LED Panel 1 Data In
ESP32 Pin 13  -->  LED Panel 2 Data In
```

### LED Panel Daisy Chain
```
ESP32 Pin 12 ──> Panel 1 (Data In)
                Panel 1 (Data Out) ──> Panel 2 (Data In)
                Panel 2 (Data Out) ──> Panel 3 (Data In)
                Panel 3 (Data Out) ──> Panel 4 (Data In)
                Panel 4 (Data Out) ──> Panel 5 (Data In)
                Panel 5 (Data Out) ──> Panel 6 (Data In)
                Panel 6 (Data Out) ──> Panel 7 (Data In)
                Panel 7 (Data Out) ──> Panel 8 (Data In)
                Panel 8 (Data Out) ──> [END]

ESP32 Pin 13 ──> Panel 9 (Data In)
                Panel 9 (Data Out) ──> Panel 10 (Data In)
                ... continue chain
```

### LED Panel Pinout (WS2812B)
```
┌─────────────────┐
│  VCC  GND  DIO  │  ← From ESP32
│  5V   GND  Data │
└─────────────────┘
```

### Wiring Steps
1. **Ground First**: Always connect GND before VCC
2. **Power Connections**:
   - Connect all panel VCC to +5V power bus
   - Connect all panel GND to GND bus
3. **Data Connections**:
   - Connect ESP32 GPIO 12 to Panel 1 DIN
   - Connect ESP32 GPIO 13 to Panel 9 DIN (if using 16 panels)
   - Connect each panel's DOUT to next panel's DIN
4. **Capacitors**: Add 1000µF capacitor at power input for noise filtering

---

## ⚡ ESP32 to Motor Driver (PCA9685)

### I2C Connection
```
ESP32 Pin 21 (SDA) ──> PCA9685 SDA
ESP32 Pin 22 (SCL) ──> PCA9685 SCL
ESP32 GND           ──> PCA9685 GND (CRITICAL!)
ESP32 3.3V or 5V    ──> PCA9685 VCC
```

### Required PCA9685 Boards
- 1 PCA9685 board supports 16 channels
- 64 motors need 4 PCA9685 boards
- All PCA9685 boards share the same I2C bus

### Addressing PCA9685 Boards
Each PCA9685 needs a unique I2C address (set via solder pads):

```
PCA9685 #1: Default address 0x40 (no solder)
PCA9685 #2: Address 0x41 (solder A0)
PCA9685 #3: Address 0x42 (solder A1)
PCA9685 #4: Address 0x43 (solder A0 + A1)
```

### Wiring Steps
1. **Common Connections** (to all PCA9685 boards):
   - Connect SDA together → ESP32 GPIO 21
   - Connect SCL together → ESP32 GPIO 22
   - Connect VCC together → ESP32 3.3V or 5V
   - Connect GND together → ESP32 GND (and motor power GND)
2. **Set Addresses** (solder address pads on each board)
3. **Add Pull-up Resistors**: 4.7kΩ on SDA and SCL to VCC

---

## 🔄 Motor Driver to Servo Motors

### Servo Motor Pinout (Standard)
```
┌───────────────┐
│  Signal  VCC  GND  │  ← Orange/White, Red, Brown/Black
│  PWM     +5V  GND  │
└───────────────┘
```

### Wiring to PCA9685
Each PCA9685 channel connects to one servo:

```
PCA9685 #1 (0x40):
  Channel 0 → Motor 1   (PWM → Signal, VCC → +5V, GND → GND)
  Channel 1 → Motor 2
  ...
  Channel 15 → Motor 16

PCA9685 #2 (0x41):
  Channel 0 → Motor 17
  ...
  Channel 15 → Motor 32

PCA9685 #3 (0x42):
  Channel 0 → Motor 33
  ...
  Channel 15 → Motor 48

PCA9685 #4 (0x43):
  Channel 0 → Motor 49
  ...
  Channel 15 → Motor 64
```

### Wiring Steps for Each Motor
1. **Signal Wire**: Connect to PCA9685 PWM output
2. **Power Wire (Red)**: Connect to motor power bus (+5V or +6V)
3. **Ground Wire (Brown/Black)**: Connect to motor power bus GND
4. **CRITICAL**: ESP32 GND, PCA9685 GND, Motor Power GND must all be connected together

---

## 📊 Wiring Diagram Summary

```
┌───────────────────────────────────────────────────────────────┐
│                        POWER SYSTEM                            │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  [USB 5V 3A]         [PSU 5V 30A+]        [PSU 5V/6V 70A+]  │
│       │                    │                    │              │
│       ▼                    ▼                    ▼              │
│  [ESP32]          ┌───────────────┐    ┌───────────────┐     │
│                   │  LED Power   │    │ Motor Power   │     │
│                   │     Bus       │    │    Bus        │     │
│                   └───────┬───────┘    └───────┬───────┘     │
│                           │                    │             │
│                           ▼                    ▼             │
│                    [8x LED Panels]      [64x Servo Motors]  │
│                                                               │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│                    DATA CONNECTIONS                           │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│                    ┌───────────┐                              │
│                    │           │                              │
│         GPIO 12 ──►│           │───► Panel 1 ──► Panel 2 ...  │
│                    │   ESP32   │                              │
│         GPIO 13 ──►│  (S3)     │───► Panel 9 ──► Panel 10 ... │
│                    │           │                              │
│         SDA 21 ────►│           │───► All PCA9685 SDA         │
│                    └───────────┘                              │
│         SCL 22 ────┴───────────┴───► All PCA9685 SCL         │
│                                                               │
│                                                               │
│         I2C Bus (SDA/SCL)                                    │
│              │                                                │
│    ┌────────┼────────┬────────┬────────┐                    │
│    ▼        ▼        ▼        ▼        ▼                    │
│ [PCA9685] [PCA9685] [PCA9685] [PCA9685]                     │
│  0x40     0x41     0x42     0x43                             │
│    │        │        │        │                             │
│    ▼        ▼        ▼        ▼                             │
│ Motors    Motors   Motors   Motors                         │
│ 1-16      17-32    33-48    49-64                           │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

## ⚠️ Safety Precautions

### MUST READ Before Powering On!

1. **Double Check Ground Connections**
   - ALL grounds must be connected together: ESP32 GND, LED GND, Motor GND, PCA9685 GND
   - Floating grounds WILL cause issues

2. **Test Power Supplies First**
   - Measure voltage with multimeter before connecting
   - Ensure correct polarity (+5V to VCC, not to GND!)

3. **Power Up in Sequence**
   1. ESP32 only (USB)
   2. LED power
   3. Motor power
   4. Never swap power and ground!

4. **Use Proper Wire Gauges**
   - Main power: 14-16 AWG
   - LED data: 22-24 AWG
   - Motor signals: 22-24 AWG

5. **Add Protection**
   - 1000µF capacitor at LED power input
   - 10µF capacitor at each PCA9685 power input
   - Fuses on main power lines (optional but recommended)

6. **Heat Management**
   - Motor drivers can get hot - add heatsinks if needed
   - Provide ventilation for power supplies

---

## 🔧 Troubleshooting Common Wiring Issues

### LED Issues
- **Problem**: LEDs not lighting up
- **Check**: 
  - Power connected (5V at panels)
  - GND common with ESP32
  - Data direction (daisy chain correct)
  - Capacitor installed at power input

- **Problem**: Random LED flickering
- **Check**:
  - Power supply sufficient current
  - Loose connections
  - Ground loops (all grounds common)

### Motor Issues
- **Problem**: Motors jittering or not moving
- **Check**:
  - I2C connection (SDA/SCL not swapped)
  - Power supply sufficient current
  - PCA9685 addresses unique
  - GND common with ESP32

- **Problem**: Only some motors work
- **Check**:
  - Which PCA9685 board they're on
  - I2C address conflicts
  - Loose connections on that board

### ESP32 Issues
- **Problem**: Not detected
- **Check**:
  - USB cable is data cable (not charge-only)
  - Drivers installed (CH340/CP2102)
  - Correct COM port selected

---

## 📝 Wiring Checklist

Use this checklist after completing wiring:

- [ ] All GND connections common (ESP32, LEDs, Motors, PCA9685)
- [ ] Power supplies measured with multimeter (correct voltage)
- [ ] LED panels in correct daisy chain order
- [ ] ESP32 GPIO 12 to first LED panel DIN
- [ ] ESP32 SDA (GPIO 21) to all PCA9685 SDA
- [ ] ESP32 SCL (GPIO 22) to all PCA9685 SCL
- [ ] Each PCA9685 has unique I2C address
- [ ] All motor signal wires connected to correct PCA9685 channels
- [ ] Motor power bus has sufficient current capacity
- [ ] Capacitors installed at power inputs
- [ ] No loose connections (tug test all wires)

---

## 🚀 Next Steps

After wiring is complete:
1. Run `python setup_wizard.py` to verify connections
2. Follow the on-screen prompts to flash firmware
3. Run automated tests
4. Launch main application: `python main.py`

---

*Last Updated: 2025-12-31*
*For issues, check the troubleshooting section or run diagnostic tests.*
