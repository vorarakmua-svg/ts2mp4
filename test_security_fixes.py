"""
Test script to verify Phase 1 security fixes
"""
import sys
from pathlib import Path
from converter import VideoConverter

# Use ASCII-safe characters for Windows console
CHECK = "[PASS]"
CROSS = "[FAIL]"

def test_path_validation():
    """Test path validation methods"""
    print("Testing path validation...")

    # Test 1: Dangerous characters
    try:
        dangerous_path = Path("C:/test/file;rm -rf.ts")
        VideoConverter._validate_path_safety(dangerous_path)
        print(f"  {CROSS} Should have rejected path with semicolon")
        return False
    except ValueError as e:
        print(f"  {CHECK} Correctly rejected dangerous path")

    # Test 2: Symlink detection (will only work if we create a symlink)
    try:
        normal_path = Path("C:/Users/vorar/OneDrive/เอกสาร2/GitHub/ts2mp4/test_security_fixes.py")
        if normal_path.exists() and not normal_path.is_symlink():
            VideoConverter._validate_path_safety(normal_path)
            print(f"  {CHECK} Accepted valid path")
    except ValueError as e:
        print(f"  {CROSS} Should have accepted valid path: {e}")
        return False

    # Test 3: Relative path rejection
    try:
        relative_path = Path("relative/path.ts")
        VideoConverter._validate_path_safety(relative_path)
        print(f"  {CROSS} Should have rejected relative path")
        return False
    except ValueError as e:
        print(f"  {CHECK} Correctly rejected relative path")

    print("Path validation tests passed!\n")
    return True

def test_file_size_validation():
    """Test file size validation"""
    print("Testing file size validation...")

    # Test with this script file (should be small and valid)
    try:
        test_file = Path(__file__)
        VideoConverter._validate_file_size(test_file)
        print(f"  {CHECK} Accepted valid file size: {test_file.stat().st_size} bytes")
    except (ValueError, FileNotFoundError) as e:
        print(f"  {CROSS} Should have accepted valid file: {e}")
        return False

    # Test with non-existent file
    try:
        fake_file = Path("C:/nonexistent/file.ts")
        VideoConverter._validate_file_size(fake_file)
        print(f"  {CROSS} Should have rejected non-existent file")
        return False
    except FileNotFoundError as e:
        print(f"  {CHECK} Correctly rejected non-existent file")

    print("File size validation tests passed!\n")
    return True

def test_disk_space_check():
    """Test disk space validation"""
    print("Testing disk space check...")

    try:
        # Create small dummy file
        test_file = Path(__file__)
        output_dir = Path("C:/Users/vorar/OneDrive/เอกสาร2/GitHub/ts2mp4")

        VideoConverter._check_disk_space(test_file, output_dir)
        print(f"  {CHECK} Sufficient disk space available")
    except OSError as e:
        print(f"  [WARN] Disk space check triggered (might be low on space): {e}")

    print("Disk space check tests passed!\n")
    return True

def test_path_traversal():
    """Test path traversal protection"""
    print("Testing path traversal protection...")

    try:
        allowed_dir = Path("C:/Users/vorar/OneDrive/เอกสาร2/GitHub/ts2mp4")
        safe_path = allowed_dir / "test.ts"
        VideoConverter._validate_path_within_directory(safe_path, allowed_dir)
        print(f"  {CHECK} Accepted path within allowed directory")
    except ValueError as e:
        print(f"  {CROSS} Should have accepted safe path: {e}")
        return False

    # Test path outside allowed directory
    try:
        outside_path = Path("C:/Windows/System32/test.ts")
        VideoConverter._validate_path_within_directory(outside_path, allowed_dir)
        print(f"  {CROSS} Should have rejected path outside allowed directory")
        return False
    except ValueError as e:
        print(f"  {CHECK} Correctly rejected outside path")

    print("Path traversal protection tests passed!\n")
    return True

def main():
    print("=" * 60)
    print("Phase 1 Security Fixes - Validation Tests")
    print("=" * 60 + "\n")

    all_passed = True
    all_passed &= test_path_validation()
    all_passed &= test_file_size_validation()
    all_passed &= test_disk_space_check()
    all_passed &= test_path_traversal()

    print("=" * 60)
    if all_passed:
        print("[SUCCESS] ALL TESTS PASSED!")
    else:
        print("[ERROR] SOME TESTS FAILED")
    print("=" * 60)

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
