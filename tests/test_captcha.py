#!/usr/bin/env python3
import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from captha import solve_captcha

def test_captcha_recognition():
    """
    Tests CAPTCHA images in tests/samples folder.
    Filename is expected to be the correct answer.
    """
    samples_dir = os.path.join(os.path.dirname(__file__), 'samples')
    if not os.path.exists(samples_dir):
        print(f"Error: {samples_dir} directory not found")
        return

    files = [f for f in os.listdir(samples_dir) if f.endswith('.png')]
    files.sort()
    
    print(f"{'Filename':<15} | {'Recognized':<15} | {'Expected':<15} | {'Status'}")
    print("-" * 65)
    
    correct = 0
    for filename in files:
        full_path = os.path.join(samples_dir, filename)
        expected = filename.split('.')[0].upper()
        
        recognized = solve_captcha(full_path)
        
        status = "OK" if recognized == expected else "FAIL"
        if status == "OK":
            correct += 1
        
        print(f"{filename:<15} | {recognized:<15} | {expected:<15} | {status}")
        
    print("-" * 65)
    acc = (correct / len(files) * 100) if files else 0
    print(f"Total: {len(files)}, Correct: {correct}, Accuracy: {acc:.1f}%")
    
    return correct, len(files)

if __name__ == "__main__":
    test_captcha_recognition()
