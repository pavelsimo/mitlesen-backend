#!/usr/bin/env python3
"""Test runner script for the Mitlesen backend."""

import subprocess
import sys
import os

def run_tests():
    """Run all tests with pytest."""
    print("🧪 Running Mitlesen Backend Tests")
    print("=" * 50)
    
    # Change to project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    # Run pytest with coverage if available
    try:
        # Try to run with coverage
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/", 
            "-v", 
            "--tb=short",
            "--color=yes"
        ], check=False)
        
        return result.returncode == 0
        
    except FileNotFoundError:
        print("❌ pytest not found. Please install pytest:")
        print("   .venv/bin/pip install pytest")
        return False

if __name__ == "__main__":
    success = run_tests()
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)