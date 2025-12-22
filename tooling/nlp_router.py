#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Natural Language Test Router
Maps user issues to appropriate test suites
"""

import re
from typing import List, Dict, Tuple
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tooling"))


class NLPRouter:
    """Routes natural language queries to appropriate test suites"""
    
    # Keyword mappings for subsystems
    MOTOR_KEYWORDS = ['motor', 'servo', 'movement', 'tracking', 'moving', 'position', 'angle']
    LED_KEYWORDS = ['led', 'display', 'light', 'silhouette', 'screen', 'showing']
    HUMAN_DETECTION_KEYWORDS = ['human', 'person', 'detect', 'tracking', 'pose', 'mediapipe']
    CONNECTION_KEYWORDS = ['connect', 'serial', 'port', 'usb', 'communication', 'esp32', 'arduino']
    
    MODE_M_KEYWORDS = ['motor mode', 'mode m', 'm mode']
    MODE_L_KEYWORDS = ['led mode', 'mode l', 'l mode']
    MODE_B_KEYWORDS = ['both mode', 'mode b', 'b mode', 'full system']
    
    def __init__(self):
        self.test_suites = {
            'connection': ['tests/hardware/esp/01_connection_test.py'],
            'motor': [
                'tests/hardware/esp/01_connection_test.py',
                'tests/hardware/esp/20_motor_driver_test.py',
                'tests/hardware/esp/30_motor_integration_test.py',
            ],
            'led': [
                'tests/hardware/esp/01_connection_test.py',
                'tests/gui/10_led_render_test.py',
                'tests/gui/20_silhouette_test.py',
            ],
            'detection': [
                'tests/gui/01_startup_test.py',
                'tests/gui/20_silhouette_test.py',
            ],
            'full': [
                'tests/hardware/esp/01_connection_test.py',
                'tests/hardware/esp/20_motor_driver_test.py',
                'tests/gui/10_led_render_test.py',
                'tests/gui/20_silhouette_test.py',
            ]
        }
    
    def parse_query(self, query: str) -> Dict[str, any]:
        """
        Parse natural language query and extract intent
        
        Args:
            query: User's natural language query
            
        Returns:
            Dictionary with parsed intent
        """
        query_lower = query.lower()
        
        # Detect subsystems
        has_motor = any(kw in query_lower for kw in self.MOTOR_KEYWORDS)
        has_led = any(kw in query_lower for kw in self.LED_KEYWORDS)
        has_detection = any(kw in query_lower for kw in self.HUMAN_DETECTION_KEYWORDS)
        has_connection = any(kw in query_lower for kw in self.CONNECTION_KEYWORDS)
        
        # Detect mode
        mode = None
        if any(kw in query_lower for kw in self.MODE_M_KEYWORDS):
            mode = 'M'
        elif any(kw in query_lower for kw in self.MODE_L_KEYWORDS):
            mode = 'L'
        elif any(kw in query_lower for kw in self.MODE_B_KEYWORDS):
            mode = 'B'
        
        # Build subsystems list
        subsystems = []
        if has_connection:
            subsystems.append('connection')
        if has_motor:
            subsystems.append('motor')
        if has_led:
            subsystems.append('led')
        if has_detection:
            subsystems.append('detection')
        
        return {
            'query': query,
            'mode': mode,
            'subsystems': subsystems,
            'requires_firmware_flash': mode is not None or has_motor or has_led,
            'confidence': self._calculate_confidence(query_lower, subsystems)
        }
    
    def _calculate_confidence(self, query_lower: str, subsystems: List[str]) -> float:
        """Calculate how confident we are in the routing"""
        if not subsystems:
            return 0.3  # Low confidence if no subsystems detected
        
        # Check for negation words
        negation_words = ['not', "doesn't", "isn't", "won't", "can't", 'no']
        has_negation = any(word in query_lower for word in negation_words)
        
        # Check for question words
        question_words = ['how', 'why', 'what', 'when', 'where']
        is_question = any(word in query_lower for word in question_words)
        
        confidence = 0.8
        if has_negation:
            confidence += 0.1  # Negation usually indicates a specific problem
        if is_question:
            confidence -= 0.2  # Questions might need clarification
        
        return min(1.0, max(0.1, confidence))
    
    def route_to_tests(self, query: str) -> Tuple[List[str], Dict]:
        """
        Route a query to appropriate test files
        
        Args:
            query: User's natural language query
            
        Returns:
            Tuple of (list of test file paths, parsed intent dict)
        """
        intent = self.parse_query(query)
        
        # If no subsystems detected, default to connection test
        if not intent['subsystems']:
            return self.test_suites['connection'], intent
        
        # Combine test lists for all detected subsystems
        test_files = []
        seen = set()
        
        # Always start with connection if any subsystem is involved
        for test in self.test_suites['connection']:
            if test not in seen:
                test_files.append(test)
                seen.add(test)
        
        # Add subsystem-specific tests
        for subsystem in intent['subsystems']:
            if subsystem in self.test_suites:
                for test in self.test_suites[subsystem]:
                    if test not in seen:
                        test_files.append(test)
                        seen.add(test)
        
        return test_files, intent
    
    def explain_routing(self, query: str):
        """Explain how a query was routed (for debugging)"""
        test_files, intent = self.route_to_tests(query)
        
        print(f"\n{'='*70}")
        print(f"NLP ROUTING ANALYSIS")
        print(f"{'='*70}")
        print(f"Query: \"{query}\"")
        print(f"\nDetected:")
        print(f"  Mode: {intent['mode'] or 'Not specified'}")
        print(f"  Subsystems: {', '.join(intent['subsystems']) or 'None detected'}")
        print(f"  Firmware Flash Needed: {'Yes' if intent['requires_firmware_flash'] else 'No'}")
        print(f"  Confidence: {intent['confidence']:.1%}")
        print(f"\nTest Files to Run ({len(test_files)}):")
        for i, test_file in enumerate(test_files, 1):
            print(f"  {i}. {test_file}")
        print(f"{'='*70}\n")


# Example usage and testing
if __name__ == "__main__":
    router = NLPRouter()
    
    # Test queries
    test_queries = [
        "motors are not moving",
        "LEDs not updating",
        "human not detected",
        "everything is broken in mode B",
        "ESP32 not connecting",
        "motors tracking but LEDs stuck"
    ]
    
    print("NLP Router Test Examples:\n")
    for query in test_queries:
        router.explain_routing(query)
        print()
