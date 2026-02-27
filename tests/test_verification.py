#!/usr/bin/env python3
"""Test verification logic for robustness against missing tickers."""

import os
import sys
import tempfile

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_verification_logic():
    """Test the verification logic with different scenarios."""

    # Test cases
    test_cases = [
        {
            "name": "Valid file with AAPL.US",
            "content": "Symbol,Date,Open,High,Low,Close,Volume\nAAPL.US,2026-02-20,180.5,182.1,179.8,181.2,50000000\nAAPL.US,2026-02-19,180.2,181.5,179.5,180.8,45000000\nAAPL.US,2026-02-18,179.8,180.5,179.0,180.2,48000000\nAAPL.US,2026-02-17,180.0,180.8,178.5,179.8,52000000\nAAPL.US,2026-02-16,179.5,180.2,178.8,180.0,47000000",
            "expected_pass": True,
            "expected_found": ["AAPL.US"]
        },
        {
            "name": "Valid file with ^SPX only",
            "content": "Symbol,Date,Open,High,Low,Close,Volume\n^SPX,2026-02-20,5000.5,5020.1,4990.8,5010.2,1000000\n^SPX,2026-02-19,5010.2,5030.5,5000.0,5025.3,1100000\n^SPX,2026-02-18,5025.3,5040.0,5015.5,5032.1,1050000\n^SPX,2026-02-17,5032.1,5050.8,5020.0,5040.5,980000\n^SPX,2026-02-16,5040.5,5055.2,5035.0,5048.0,1020000",
            "expected_pass": True,
            "expected_found": ["^SPX"]
        },
        {
            "name": "Valid file with ^DJI only",
            "content": "Symbol,Date,Open,High,Low,Close,Volume\n^DJI,2026-02-20,38000.5,38200.1,37900.8,38100.2,500000\n^DJI,2026-02-19,38100.2,38300.5,38000.0,38250.3,480000\n^DJI,2026-02-18,38250.3,38400.0,38150.5,38320.1,520000\n^DJI,2026-02-17,38320.1,38450.8,38200.0,38400.5,490000\n^DJI,2026-02-16,38400.5,38500.2,38350.0,38480.0,510000",
            "expected_pass": True,
            "expected_found": ["^DJI"]
        },
        {
            "name": "Valid file with GLD.US only",
            "content": "Symbol,Date,Open,High,Low,Close,Volume\nGLD.US,2026-02-20,185.5,186.1,184.8,185.2,3000000\nGLD.US,2026-02-19,185.2,185.8,184.5,185.5,2800000\nGLD.US,2026-02-18,185.5,186.2,185.0,185.8,3200000\nGLD.US,2026-02-17,185.8,186.5,185.3,186.0,2900000\nGLD.US,2026-02-16,186.0,186.8,185.5,186.3,3100000",
            "expected_pass": True,
            "expected_found": ["GLD.US"]
        },
        {
            "name": "Valid file with multiple tickers",
            "content": "Symbol,Date,Open,High,Low,Close,Volume\nAAPL.US,2026-02-20,180.5,182.1,179.8,181.2,50000000\n^SPX,2026-02-20,5000.5,5020.1,4990.8,5010.2,1000000\n^DJI,2026-02-20,38000.5,38200.1,37900.8,38100.2,500000\nAAPL.US,2026-02-19,180.2,181.5,179.5,180.8,45000000\n^SPX,2026-02-19,5010.2,5030.5,5000.0,5025.3,1100000",
            "expected_pass": True,
            "expected_found": ["AAPL.US", "^SPX", "^DJI"]
        },
        {
            "name": "Unauthorized content",
            "content": "Unauthorized access. Please login to continue.",
            "expected_pass": False,
            "expected_found": []
        },
        {
            "name": "Empty file",
            "content": "",
            "expected_pass": False,
            "expected_found": []
        },
        {
            "name": "File with < 5 rows",
            "content": "Symbol,Date,Open,High,Low,Close,Volume\nXYZ,2026-02-20,100,101,99,100,1000",
            "expected_pass": False,
            "expected_found": []
        },
        {
            "name": "Valid file with unknown ticker (should still pass with common tickers)",
            "content": "Symbol,Date,Open,High,Low,Close,Volume\nAAPL.US,2026-02-20,180.5,182.1,179.8,181.2,50000000\nXYZ.UK,2026-02-20,50,51,49,50,5000\nAAPL.US,2026-02-19,180.2,181.5,179.5,180.8,45000000\nXYZ.UK,2026-02-19,49,50,48,49,4800\nAAPL.US,2026-02-18,179.8,180.5,179.0,180.2,48000000",
            "expected_pass": True,
            "expected_found": ["AAPL.US"]
        },
        {
            "name": "File with NO verification markers (should fail)",
            "content": "Symbol,Date,Open,High,Low,Close,Volume\nXYZ.UK,2026-02-20,50,51,49,50,5000\nABC.DE,2026-02-20,100,101,99,100,10000\nLMN.FR,2026-02-20,75,76,74,75,8000\nGHI.IT,2026-02-20,25,26,24,25,20000\nJKL.ES,2026-02-20,30,31,29,30,15000",
            "expected_pass": False,
            "expected_found": []
        }
    ]

    print("Testing Verification Logic")
    print("=" * 60)

    all_passed = True
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print("-" * 60)

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(test['content'])
            temp_path = f.name

        try:
            # Read and verify
            with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                content = "".join(lines)
                row_count = max(0, len(lines) - 1)

            print(f"  Rows: {row_count}")

            # Verification logic (from main.py)
            row_failed = False
            found_markers = []
            if "Unauthorized" in content:
                print(f"  Result: FAIL (Unauthorized)")
                row_failed = True
            elif row_count < 5:
                print(f"  Result: FAIL (Insufficient data: {row_count} rows)")
                row_failed = True
            else:
                env_markers = os.getenv("STOOQ_VERIFICATION_MARKERS", "")
                required_markers = [m.strip() for m in env_markers.split(",") if m.strip()] if env_markers else ["AAPL.US", "^SPX", "^DJI", "GLD.US"]

                found_markers = [m for m in required_markers if m in content]
                missing_markers = [m for m in required_markers if m not in content]

                if found_markers:
                    print(f"  Result: PASS")
                    print(f"  Found: {', '.join(found_markers)}")
                    if missing_markers:
                        print(f"  Missing: {', '.join(missing_markers)}")
                else:
                    print(f"  Result: FAIL (No verification markers found)")
                    print(f"  Required: {', '.join(required_markers)}")
                    row_failed = True

            # Check if result matches expected
            passed = not row_failed
            if passed == test['expected_pass']:
                if found_markers == test['expected_found'] or (not test['expected_found'] and not found_markers):
                    print("  ✅ Test PASSED")
                else:
                    print(f"  ⚠️  Test PASSED but markers differ (expected: {test['expected_found']}, got: {found_markers})")
            else:
                print(f"  ❌ Test FAILED (expected: {'PASS' if test['expected_pass'] else 'FAIL'}, got: {'PASS' if passed else 'FAIL'})")
                all_passed = False

        finally:
            os.unlink(temp_path)

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(test_verification_logic())
