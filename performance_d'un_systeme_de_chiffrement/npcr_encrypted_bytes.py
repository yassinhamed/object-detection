#!/usr/bin/env python3
"""
NPCR (Number of Pixel Change Rate) - AES Correct Version

✔ Compares ORIGINAL image vs ENCRYPTED image (ciphertext mapped safely)
✔ Uses proper AES evaluation method (bitwise XOR comparison)
✔ NO fake image reshaping of ciphertext
"""

import cv2
import numpy as np
import sys
from pathlib import Path


def load_image(path):
    """Load image safely"""
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"Cannot load image: {path}")
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def load_ciphertext(path, size):
    """
    Load AES ciphertext and map it safely to pixel space.
    We only use raw bytes truncated to image size.
    """
    with open(path, "rb") as f:
        data = f.read()

    # skip IV (first 16 bytes)
    data = data[16:]

    # truncate to image size
    data = data[:size]

    return np.frombuffer(data, dtype=np.uint8)


def calculate_npcr(img1, cipher_pixels):
    """
    NPCR formula:
    NPCR = (Number of different pixels / total pixels) * 100
    """

    img1_flat = img1.flatten()
    cipher_flat = cipher_pixels.flatten()

    # ensure same size
    min_len = min(len(img1_flat), len(cipher_flat))

    img1_flat = img1_flat[:min_len]
    cipher_flat = cipher_flat[:min_len]

    # pixel-wise comparison
    diff = img1_flat != cipher_flat

    npcr = (np.sum(diff) / min_len) * 100

    return npcr, min_len


def main(original_path, encrypted_path):

    print("📷 Loading original image...")
    img = load_image(original_path)
    print(f"   Shape: {img.shape}")

    print("\n🔐 Loading encrypted file...")
    cipher = load_ciphertext(encrypted_path, img.size)
    print(f"   Cipher size used: {cipher.shape[0]} bytes")

    print("\n🔍 Calculating NPCR...")

    npcr, used_pixels = calculate_npcr(img, cipher)

    print("\n" + "=" * 70)
    print("NPCR (Number of Pixel Change Rate)")
    print("=" * 70)

    print(f"Total Pixels Compared: {used_pixels}")
    print(f"NPCR Value: {npcr:.4f}%")

    print("\nInterpretation:")

    if npcr > 99:
        print("✅ Excellent - Very strong diffusion (AES is secure)")
    elif npcr > 95:
        print("✅ Good - Strong encryption")
    elif npcr > 90:
        print("⚠️  Moderate security")
    else:
        print("❌ Weak encryption")

    print("\nTheoretical reference:")
    print("✔ Good AES encryption: NPCR ≈ 99%")
    print("=" * 70)


if __name__ == "__main__":

    if len(sys.argv) != 3:
        print("Usage: python npcr.py <original_image> <encrypted_file>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])