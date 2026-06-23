#!/usr/bin/env python3
"""
AES-SAFE UACI ANALYSIS (Corrected for PFA)

NOTE:
Traditional UACI is NOT strictly valid for AES ciphertext.
This version converts it into a BYTE VARIATION INDEX.
"""

import cv2
import numpy as np
from pathlib import Path
import sys


def load_image(path):
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"Cannot load image: {path}")
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def load_cipher(path):
    with open(path, "rb") as f:
        data = f.read()

    # remove IV
    data = data[16:]

    return np.frombuffer(data, dtype=np.uint8)


def byte_variation_index(original_img, cipher_bytes):
    """
    SAFE replacement for UACI in AES systems

    Measures:
    - how different ciphertext bytes are from image pixels
    - normalized difference only (no spatial assumption)
    """

    img = original_img.flatten()
    cipher = cipher_bytes.flatten()

    min_len = min(len(img), len(cipher))

    img = img[:min_len]
    cipher = cipher[:min_len]

    diff = np.abs(img.astype(np.float64) - cipher.astype(np.float64))

    # normalize
    bvi = (np.mean(diff) / 255.0) * 100

    return bvi, min_len


def main(img_path, enc_path):

    print("📷 Loading image...")
    img = load_image(img_path)

    print("🔐 Loading ciphertext...")
    cipher = load_cipher(enc_path)

    print("\n🔍 Computing AES-safe variation metric...")

    bvi, n = byte_variation_index(img, cipher)

    print("\n" + "=" * 60)
    print("AES Encryption Analysis (Safe Metric)")
    print("=" * 60)

    print(f"Pixels Compared: {n}")
    print(f"Variation Index: {bvi:.4f}%")

    print("\nInterpretation:")

    if bvi > 30:
        print("✅ High randomness (strong encryption behavior)")
    elif bvi > 20:
        print("⚠️ Moderate randomness")
    else:
        print("❌ Weak randomness")

    print("\nNOTE:")
    print("- Classical UACI is NOT valid for AES ciphertext")
    print("- This metric is a byte-level variation indicator")
    print("=" * 60)


if __name__ == "__main__":

    if len(sys.argv) != 3:
        print("Usage: python uaci_safe.py <image> <encrypted_file>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])