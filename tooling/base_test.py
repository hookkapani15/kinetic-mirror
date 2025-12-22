#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Test Class for Mirror Project
All tests inherit from this to ensure consistent JSON output format
"""

import json
import time
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from pathlib import Path


class BaseTest(ABC):
    """Base class for all mirror project tests"""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.start_time = None
        self.end_time = None
        self.result = {
            "test_name": test_name,
            "status": "not_run",
            "details": "",
            "metrics": {},
            "learns": {},
            "suggested_actions": [],
            "confidence": 0.0,
            "execution_time_ms": 0
        }
    
    @abstractmethod
    def run(self) -> Dict[str, Any]:
        """
        Execute the test. Must be implemented by subclasses.
        
        Returns:
            Dict with test results in standard format
        """
        pass
    
    def execute(self) -> Dict[str, Any]:
        """
        Wrapper that handles timing and exception catching
        
        Returns:
            Test result dictionary
        """
        self.start_time = time.time()
        
        try:
            # Run the actual test
            result = self.run()
            
            # Ensure result has all required fields
            self.result.update(result)
            
            # Default to pass if no status set
            if self.result["status"] == "not_run":
                self.result["status"] = "pass"
                
        except Exception as e:
            self.result["status"] = "fail"
            self.result["details"] = f"Test crashed: {str(e)}"
            self.result["suggested_actions"].append(f"Fix exception: {type(e).__name__}")
            import traceback
            self.result["metrics"]["traceback"] = traceback.format_exc()
        
        self.end_time = time.time()
        self.result["execution_time_ms"] = int((self.end_time - self.start_time) * 1000)
        
        return self.result
    
    def pass_test(self, details: str = "", **kwargs):
        """Mark test as passed"""
        return {
            "status": "pass",
            "details": details,
            **kwargs
        }
    
    def fail_test(self, details: str, suggested_actions: List[str] = None, **kwargs):
        """Mark test as failed with suggestions"""
        return {
            "status": "fail",
            "details": details,
            "suggested_actions": suggested_actions or [],
            **kwargs
        }
    
    def skip_test(self, reason: str):
        """Mark test as skipped"""
        return {
            "status": "skipped",
            "details": f"Test skipped: {reason}"
        }


class TestSuite:
    """Collection of tests that can be run together"""
    
    def __init__(self, suite_name: str, tests: List[BaseTest] = None):
        self.suite_name = suite_name
        self.tests = tests or []
        self.results = []
    
    def add_test(self, test: BaseTest):
        """Add a test to the suite"""
        self.tests.append(test)
    
    def run_all(self, stop_on_failure: bool = False) -> List[Dict[str, Any]]:
        """
        Run all tests in the suite
        
        Args:
            stop_on_failure: If True, stop running tests after first failure
            
        Returns:
            List of test results
        """
        self.results = []
        
        for test in self.tests:
            print(f"Running: {test.test_name}...", end=" ")
            result = test.execute()
            self.results.append(result)
            
            status_symbol = "[PASS]" if result["status"] == "pass" else "[FAIL]"
            print(f"{status_symbol} {result['status'].upper()}")
            
            if result["status"] == "fail" and stop_on_failure:
                print(f"[!] Stopping test suite due to failure in: {test.test_name}")
                break
        
        return self.results
    
    def print_summary(self):
        """Print a summary of test results"""
        if not self.results:
            print("No tests run")
            return
        
        passed = sum(1 for r in self.results if r["status"] == "pass")
        failed = sum(1 for r in self.results if r["status"] == "fail")
        skipped = sum(1 for r in self.results if r["status"] == "skipped")
        total = len(self.results)
        
        print("\n" + "="*70)
        print(f"TEST SUITE: {self.suite_name}")
        print("="*70)
        print(f"Total: {total} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
        
        if failed > 0:
            print("\n[FAILED TESTS]:")
            for result in self.results:
                if result["status"] == "fail":
                    print(f"  • {result['test_name']}: {result['details']}")
                    if result.get("suggested_actions"):
                        for action in result["suggested_actions"]:
                            print(f"    -> {action}")
        
        print("="*70 + "\n")
    
    def save_results(self, output_path: Path):
        """Save test results to JSON file"""
        output_data = {
            "suite_name": self.suite_name,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r["status"] == "pass"),
                "failed": sum(1 for r in self.results if r["status"] == "fail"),
                "skipped": sum(1 for r in self.results if r["status"] == "skipped"),
            },
            "results": self.results
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"[OK] Results saved to: {output_path}")
