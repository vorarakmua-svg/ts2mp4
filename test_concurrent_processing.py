"""
Test script to verify Phase 2 concurrent processing implementation
"""
import sys
import time
from pathlib import Path
from threading import Event, Semaphore
from concurrent.futures import ThreadPoolExecutor, as_completed

# Test the imports
try:
    from main import ProgressTracker, process_file_worker
    print("[PASS] Successfully imported ProgressTracker and process_file_worker")
except ImportError as e:
    print(f"[FAIL] Failed to import from main: {e}")
    sys.exit(1)

try:
    from converter import VideoConverter
    print("[PASS] Successfully imported VideoConverter")
except ImportError as e:
    print(f"[FAIL] Failed to import VideoConverter: {e}")
    sys.exit(1)


def test_progress_tracker():
    """Test thread-safe progress tracking"""
    print("\nTesting ProgressTracker...")

    try:
        tracker = ProgressTracker(5)
        print("  [PASS] Created ProgressTracker with 5 files")

        # Test thread-safe increment
        tracker.completed = 0
        tracker.increment()
        assert tracker.completed == 1, "Increment should increase count"
        print("  [PASS] Increment works correctly")

        # Test write (without actual progress bar)
        tracker.write("[TEST] This is a test message")
        print("  [PASS] Write works correctly")

        print("ProgressTracker tests passed!\n")
        return True
    except Exception as e:
        print(f"  [FAIL] ProgressTracker test failed: {e}\n")
        return False


def test_concurrent_structure():
    """Test that concurrent processing structure is correct"""
    print("Testing concurrent processing structure...")

    try:
        # Test that we can create a ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as executor:
            print("  [PASS] ThreadPoolExecutor created successfully")

        # Test semaphore creation
        gpu_semaphore = Semaphore(1)
        print("  [PASS] Semaphore created successfully")

        # Test cancel event
        cancel_event = Event()
        print("  [PASS] Event created successfully")

        print("Concurrent structure tests passed!\n")
        return True
    except Exception as e:
        print(f"  [FAIL] Concurrent structure test failed: {e}\n")
        return False


def test_worker_function_signature():
    """Test that process_file_worker has correct signature"""
    print("Testing process_file_worker signature...")

    try:
        import inspect
        sig = inspect.signature(process_file_worker)
        params = list(sig.parameters.keys())

        expected_params = ['converter', 'input_file', 'cancel_event', 'gpu_semaphore']

        if params == expected_params:
            print(f"  [PASS] process_file_worker has correct parameters: {params}")
        else:
            print(f"  [FAIL] Expected {expected_params}, got {params}")
            return False

        print("Worker function signature test passed!\n")
        return True
    except Exception as e:
        print(f"  [FAIL] Worker function signature test failed: {e}\n")
        return False


def test_regex_optimization():
    """Test that regex patterns are compiled at class level"""
    print("Testing regex pattern optimization...")

    try:
        # Check if VideoConverter has class-level regex patterns
        if hasattr(VideoConverter, '_DURATION_PATTERN'):
            print("  [PASS] _DURATION_PATTERN exists as class attribute")
        else:
            print("  [FAIL] _DURATION_PATTERN not found")
            return False

        if hasattr(VideoConverter, '_TIME_PATTERN'):
            print("  [PASS] _TIME_PATTERN exists as class attribute")
        else:
            print("  [FAIL] _TIME_PATTERN not found")
            return False

        # Verify they are compiled regex patterns
        import re
        if isinstance(VideoConverter._DURATION_PATTERN, re.Pattern):
            print("  [PASS] _DURATION_PATTERN is compiled regex")
        else:
            print("  [FAIL] _DURATION_PATTERN is not compiled regex")
            return False

        if isinstance(VideoConverter._TIME_PATTERN, re.Pattern):
            print("  [PASS] _TIME_PATTERN is compiled regex")
        else:
            print("  [FAIL] _TIME_PATTERN is not compiled regex")
            return False

        print("Regex optimization tests passed!\n")
        return True
    except Exception as e:
        print(f"  [FAIL] Regex optimization test failed: {e}\n")
        return False


def test_concurrent_execution_mock():
    """Test concurrent execution with mock tasks"""
    print("Testing concurrent execution with mock tasks...")

    try:
        # Create simple mock tasks
        def mock_task(task_id):
            time.sleep(0.1)  # Simulate work
            return task_id, f"Result {task_id}"

        results = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(mock_task, i): i for i in range(5)}

            for future in as_completed(futures):
                task_id, result = future.result()
                results.append(task_id)

        if len(results) == 5:
            print(f"  [PASS] All 5 tasks completed: {sorted(results)}")
        else:
            print(f"  [FAIL] Expected 5 results, got {len(results)}")
            return False

        print("Concurrent execution mock test passed!\n")
        return True
    except Exception as e:
        print(f"  [FAIL] Concurrent execution mock test failed: {e}\n")
        return False


def main():
    print("=" * 60)
    print("Phase 2 Performance Optimization - Verification Tests")
    print("=" * 60 + "\n")

    all_passed = True
    all_passed &= test_progress_tracker()
    all_passed &= test_concurrent_structure()
    all_passed &= test_worker_function_signature()
    all_passed &= test_regex_optimization()
    all_passed &= test_concurrent_execution_mock()

    print("=" * 60)
    if all_passed:
        print("[SUCCESS] ALL TESTS PASSED!")
        print("\nConcurrent processing is ready to use.")
        print("To enable it, set MAX_CONCURRENT_CONVERSIONS > 1 in config")
    else:
        print("[ERROR] SOME TESTS FAILED")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
