#!/usr/bin/env python3
"""
Correlation Comparison (Original vs Decrypted Image)
PFA-ready correct evaluation
"""

import cv2
import numpy as np
import sys


def load_image(path):
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"Cannot load image: {path}")
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float64)


def correlation(a, b):
    return np.corrcoef(a.flatten(), b.flatten())[0, 1]


def main(img1_path, img2_path):

    img1 = load_image(img1_path)
    img2 = load_image(img2_path)

    print("==================================================")
    print("CORRELATION COMPARISON")
    print("==================================================")

    print(f"Image 1: {img1_path}")
    print(f"Image 2: {img2_path}")

    corr = correlation(img1, img2)

    print("\n-----------------------------")
    print(f"Correlation: {corr:.6f}")
    print("-----------------------------")

    print("\nInterpretation:")
    if corr > 0.95:
        print("✔ Images are almost identical (correct decryption)")
    elif corr > 0.5:
        print("⚠ Moderate similarity")
    else:
        print("❌ Low similarity (possible decryption error)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python correlation_compare.py img1 img2")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])