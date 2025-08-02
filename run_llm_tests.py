#!/usr/bin/env python3
"""
Test runner for LLM inference tests using pytest.
"""

import sys
import subprocess
from pathlib import Path


def run_llm_tests():
    """Run LLM inference tests using pytest."""
    print("🧪 Running LLM Inference Tests with pytest")
    print("=" * 60)
    
    # Check if test files exist
    test_videos = [
        "tests/data/criminal.mp4",
        "tests/data/gate-static.mp4"
    ]
    
    missing_files = []
    for video_path in test_videos:
        if not Path(video_path).exists():
            missing_files.append(video_path)
    
    if missing_files:
        print("❌ Missing test video files:")
        for file in missing_files:
            print(f"   - {file}")
        print("\nPlease ensure the test video files are copied to tests/data/")
        return 1
    
    print("✅ All test video files found")
    print()
    
    # Run pytest with specific options
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_llm_inference.py",
        "-v",
        "-s",
        "--tb=short",
        "--disable-warnings",
        "--capture=no",
        "-m", "llm",  # Only run LLM tests
        "--color=yes"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        return 1


def run_unit_tests():
    """Run only unit tests (no LLM inference)."""
    print("🧪 Running Unit Tests")
    print("=" * 40)
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_llm_inference.py",
        "-v",
        "-s",
        "--tb=short",
        "--disable-warnings",
        "--capture=no",
        "-m", "unit",  # Only run unit tests
        "--color=yes"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        return 1


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "unit":
            return run_unit_tests()
        elif sys.argv[1] == "help":
            print("Usage:")
            print("  python run_llm_tests.py          # Run LLM inference tests")
            print("  python run_llm_tests.py unit     # Run unit tests only")
            print("  python run_llm_tests.py help     # Show this help")
            return 0
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Use 'python run_llm_tests.py help' for usage information")
            return 1
    
    return run_llm_tests()


if __name__ == "__main__":
    sys.exit(main()) 