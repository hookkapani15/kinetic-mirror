#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor Controller for Mirror Body Animations
Handles servo angle calculations and packet packing for ESP32 control
"""

import numpy as np
import struct

class MotorController:
    def __init__(self, num_servos=6, angle_min=0, angle_max=180):
        self.num_servos = num_servos
        self.angle_min = angle_min
        self.angle_max = angle_max

    def calculate_angles(self, pose_results):
        """
        Calculate servo angles based on human pose
        Maps human X position (0.0-1.0) to servo angles (0-180°)
        """
        angles = [90] * self.num_servos  # Default to neutral position

        if pose_results and pose_results.pose_landmarks:
            # Get human center X position
            landmarks = pose_results.pose_landmarks.landmark

            # Use nose or center of shoulders for X position
            if len(landmarks) > 0:
                # Try nose first (landmark 0)
                if landmarks[0].visibility > 0.8:
                    human_x = landmarks[0].x
                else:
                    # Fallback to average of shoulder positions
                    # FIXED: Check len(landmarks) > 12 to safely access indices 11 AND 12
                    left_shoulder = landmarks[11] if len(landmarks) > 12 else None
                    right_shoulder = landmarks[12] if len(landmarks) > 12 else None
                    if left_shoulder and right_shoulder and left_shoulder.visibility > 0.8 and right_shoulder.visibility > 0.8:
                        human_x = (left_shoulder.x + right_shoulder.x) / 2
                    else:
                        human_x = 0.5  # Default center if no good landmarks

                # ADDED: Validate human_x to prevent NaN/inf propagation
                if not np.isfinite(human_x) or human_x < 0 or human_x > 1:
                    human_x = 0.5  # Default to center if invalid
                
                # Map X position (0.0-1.0) to angle range (0-180°)
                # Left side (x=0) = 0°, Right side (x=1) = 180°, Center (x=0.5) = 90°
                target_angle = human_x * 180.0

                # ADDED: Validate target_angle is finite
                if not np.isfinite(target_angle):
                    target_angle = 90.0
                
                # Clamp to valid range
                target_angle = max(self.angle_min, min(self.angle_max, target_angle))

                # Apply to all servos (can be modified for different servo behaviors)
                angles = [int(target_angle)] * self.num_servos

        return angles

    def pack_servo_packet(self, angles):
        """
        Pack servo angles into firmware-compatible packet.
        Firmware expects:
          [0xAA, 0xBB, 0x02, servo1_hi, servo1_lo, ..., servo6_hi, servo6_lo]
        Each servo value is a uint16 representing 0-1000 (mapped to 0-180°).
        Total length = 15 bytes.
        """
        if len(angles) != self.num_servos:
            raise ValueError(f"Expected {self.num_servos} angles, got {len(angles)}")

        packet = [0xAA, 0xBB, 0x02]

        for angle in angles:
            # Normalize and clamp angle
            angle = int(angle) if hasattr(angle, "item") else int(angle)
            angle = max(self.angle_min, min(self.angle_max, angle))

            # Map 0-180 deg -> 0-1000 (matches firmware map(value, 0..1000, 0..180))
            value = int((angle / 180.0) * 1000)
            value = max(0, min(1000, value))

            # Big-endian two bytes per servo
            packet.append((value >> 8) & 0xFF)
            packet.append(value & 0xFF)

        return bytes(packet)
