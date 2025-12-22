#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Test Runner
Orchestrates test execution based on natural language input or direct test suite selection
"""

import sys
import json
from pathlib import Path
from typing import List, Optional
import importlib.util

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tooling"))
sys.path.insert(0, str(REPO_ROOT / "tests"))

from base_test import TestSuite, BaseTest
from nlp_router import NLPRouter


class TestRunner:
    """Main test orchestration engine"""
    
    def __init__(self):
        self.nlp_router = NLPRouter()
        self.settings_dir = REPO_ROOT / "settings"
        self.settings_dir.mkdir(exist_ok=True)
    
    def load_test_from_file(self, test_path: Path) -> Optional[BaseTest]:
        """
        Dynamically load a test class from a Python file
        
        Args:
            test_path: Path to test file
            
        Returns:
            Instantiated test object or None
        """
        if not test_path.exists():
            print(f"[!] Test file not found: {test_path}")
            return None
        
        try:
            # Load module dynamically
            spec = importlib.util.spec_from_file_location("test_module", test_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find BaseTest subclass
            for item_name in dir(module):
                item = getattr(module, item_name)
                if (isinstance(item, type) and 
                    issubclass(item, BaseTest) and 
                    item is not BaseTest):
                    return item()  # Instantiate test
            
            print(f"[!] No test class found in: {test_path}")
            return None
            
        except Exception as e:
            print(f"[!] Failed to load test {test_path}: {e}")
            return None
    
    def run_from_query(self, query: str, stop_on_failure: bool = True) -> TestSuite:
        """
        Run tests based on natural language query
        
        Args:
            query: Natural language description of the issue
            stop_on_failure: Stop after first failure
            
        Returns:
            TestSuite with results
        """
        print(f"\n[*] Interpreting query: \"{query}\"")
        
        # Route query to tests
        test_files, intent = self.nlp_router.route_to_tests(query)
        
        print(f"[OK] Detected {len(intent['subsystems'])} subsystem(s): {', '.join(intent['subsystems']) or 'connection only'}")
        print(f"[OK] Confidence: {intent['confidence']:.0%}")
        
        if intent['requires_firmware_flash']:
            mode = intent['mode'] or 'current'
            print(f"\n[!] FIRMWARE FLASH REQUIRED for mode: {mode}")
            print("   (Auto-flashing not yet implemented - manual flash needed)")
        
        # Build test suite
        suite = TestSuite(f"NLP Query: {query[:50]}...")
        
        for test_file_rel in test_files:
            test_path = REPO_ROOT / test_file_rel
            test = self.load_test_from_file(test_path)
            if test:
                suite.add_test(test)
        
        if not suite.tests:
            print("[!] No tests loaded!")
            return suite
        
        print(f"\n[TEST] Running {len(suite.tests)} test(s)...\n")
        
        # Run tests
        suite.run_all(stop_on_failure=stop_on_failure)
        
        # Save results
        results_file = self.settings_dir / "test_results.json"
        suite.save_results(results_file)
        
        # Update learns
        self._update_learns(suite.results)
        
        return suite
    
    def run_test_files(self, test_files: List[str], suite_name: str = "Manual Test Run") -> TestSuite:
        """
        Run specific test files directly
        
        Args:
            test_files: List of test file paths
            suite_name: Name for the test suite
            
        Returns:
            TestSuite with results
        """
        suite = TestSuite(suite_name)
        
        for test_file in test_files:
            test_path = REPO_ROOT / test_file
            test = self.load_test_from_file(test_path)
            if test:
                suite.add_test(test)
        
        print(f"\n[TEST] Running {len(suite.tests)} test(s)...\n")
        suite.run_all()
        
        # Save results
        results_file = self.settings_dir / "test_results.json"
        suite.save_results(results_file)
        
        return suite
    
    def _update_learns(self, results: List[dict]):
        """Update the learning database with new information"""
        learns_file = self.settings_dir / "test_learns.json"
        
        # Load existing learns
        if learns_file.exists():
            with open(learns_file) as f:
                all_learns = json.load(f)
        else:
            all_learns = {}
        
        # Collect new learns from results
        for result in results:
            if result.get('learns'):
                all_learns.update(result['learns'])
        
        # Save updated learns
        with open(learns_file, 'w') as f:
            json.dump(all_learns, f, indent=2)


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Mirror Project Test Runner')
    parser.add_argument('query', nargs='*', help='Natural language test query')
    parser.add_argument('--files', '-f', nargs='+', help='Specific test files to run')
    parser.add_argument('--continue', '-c', action='store_true', dest='continue_on_failure',
                       help='Continue running tests after failures')
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    if args.files:
        # Run specific files
        suite = runner.run_test_files(args.files)
    elif args.query:
        # Run from natural language query
        query = ' '.join(args.query)
        suite = runner.run_from_query(query, stop_on_failure=not args.continue_on_failure)
    else:
        # Interactive mode
        print("Mirror Project Test Runner")
        print("=" * 70)
        print("Enter a description of the issue (or 'quit' to exit):")
        print("Examples:")
        print("  - motors not moving")
        print("  - LEDs not updating")
        print("  - human not detected in mode B")
        print()
        
        while True:
            query = input("\n> ").strip()
            if query.lower() in ['quit', 'exit', 'q']:
                break
            if not query:
                continue
            
            suite = runner.run_from_query(query)
            suite.print_summary()
    
    # Print summary if not in interactive mode
    if args.files or args.query:
        suite.print_summary()


if __name__ == "__main__":
    main()
