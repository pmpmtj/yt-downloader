#!/usr/bin/env python3
"""
Test runner script for YouTube Downloader testing framework.

This script provides convenient commands for running different test suites
and generating coverage reports.

python run_tests.py all
"""

import sys
import subprocess
import argparse
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors gracefully."""
    print(f"🚀 {description}")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print("Output:", result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print("Error:", e.stderr)
        print("Return code:", e.returncode)
        return False

def install_dependencies():
    """Install test dependencies."""
    cmd = [sys.executable, "-m", "pip", "install", "-e", ".[test]"]
    return run_command(cmd, "Installing test dependencies")

def run_unit_tests():
    """Run unit tests only."""
    cmd = [sys.executable, "-m", "pytest", "tests/unit/", "-v", "-m", "unit"]
    return run_command(cmd, "Running unit tests")

def run_integration_tests():
    """Run integration tests only."""
    cmd = [sys.executable, "-m", "pytest", "tests/integration/", "-v", "-m", "integration"]
    return run_command(cmd, "Running integration tests")

def run_all_tests():
    """Run all tests with coverage."""
    cmd = [
        sys.executable, "-m", "pytest", 
        "tests/", 
        "-v", 
        "--cov=src/my_project", 
        "--cov-report=html:htmlcov",
        "--cov-report=term-missing"
    ]
    return run_command(cmd, "Running all tests with coverage")

def run_fast_tests():
    """Run fast tests only (exclude slow tests)."""
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v", "-m", "not slow"]
    return run_command(cmd, "Running fast tests")

def run_network_tests():
    """Run network-dependent tests."""
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v", "-m", "network"]
    return run_command(cmd, "Running network tests")

def lint_tests():
    """Run linting on test files."""
    cmd = [sys.executable, "-m", "pytest", "--flake8", "tests/"]
    return run_command(cmd, "Linting test files")

def main():
    parser = argparse.ArgumentParser(description="YouTube Downloader Test Runner")
    parser.add_argument("command", nargs="?", default="all", 
                       choices=["install", "unit", "integration", "all", "fast", "network", "lint"],
                       help="Test command to run")
    
    args = parser.parse_args()
    
    print("🧪 YouTube Downloader Testing Framework")
    print("=" * 50)
    
    if args.command == "install":
        success = install_dependencies()
    elif args.command == "unit":
        success = run_unit_tests()
    elif args.command == "integration":
        success = run_integration_tests()
    elif args.command == "all":
        success = run_all_tests()
    elif args.command == "fast":
        success = run_fast_tests()
    elif args.command == "network":
        success = run_network_tests()
    elif args.command == "lint":
        success = lint_tests()
    else:
        print(f"Unknown command: {args.command}")
        success = False
    
    if success:
        print(f"\n✅ Test execution completed successfully!")
        print("📊 Check htmlcov/index.html for detailed coverage report")
    else:
        print(f"\n❌ Test execution failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
