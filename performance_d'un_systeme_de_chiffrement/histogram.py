#!/usr/bin/env python3
"""
Histogram Analysis for AES Image Encryption
Shows distribution of pixel values vs ciphertext bytes
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
import sys
from pathlib import Path


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


def plot_histograms(image_path, enc_path):

    print("📷 Loading original image...")
    img = load_image(image_path)

    print("🔐 Loading encrypted file...")
    cipher = load_cipher(enc_path)

    print("\n📊 Generating histograms...")

    plt.figure(figsize=(12, 5))

    # ORIGINAL IMAGE HISTOGRAM
    plt.subplot(1, 2, 1)
    plt.hist(img.flatten(), bins=256, color='blue', alpha=0.7)
    plt.title("Original Image Histogram")
    plt.xlabel("Pixel Value")
    plt.ylabel("Frequency")

    # ENCRYPTED DATA HISTOGRAM
    plt.subplot(1, 2, 2)
    plt.hist(cipher.flatten(), bins=256, color='red', alpha=0.7)
    plt.title("Encrypted Data Histogram")
    plt.xlabel("Byte Value")
    plt.ylabel("Frequency")

    plt.tight_layout()
    plt.show()

    print("\n==================================================")
    print("Histogram Analysis Complete")
    print("==================================================")
    print("✔ Original: structured distribution (image content)")
    print("✔ Encrypted: uniform distribution (randomness)")
    print("✔ Good encryption → flat histogram")
    print("==================================================")


if __name__ == "__main__":

    if len(sys.argv) != 3:
        print("Usage: python histogram.py <image> <encrypted_file>")
        sys.exit(1)

    plot_histograms(sys.argv[1], sys.argv[2])