#!/usr/bin/env python3

import time
from image_encryption import ImageEncryption
import sys


def measure_encryption_time(image_path):

    encryptor = ImageEncryption()

    start_time = time.time()

    output = encryptor.encrypt_file(image_path)

    end_time = time.time()

    duration = end_time - start_time

    print("\n" + "=" * 50)
    print("⏱️ Encryption Time Analysis")
    print("=" * 50)
    print(f"File: {image_path}")
    print(f"Encrypted file: {output}")
    print(f"Execution time: {duration:.4f} seconds")
    print("=" * 50)

    if duration < 1:
        print("✅ Very fast encryption")
    elif duration < 3:
        print("⚠️ Moderate speed")
    else:
        print("❌ Slow encryption")

    print("=" * 50)


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Usage: python encryption_time.py <image>")
        sys.exit(1)

    measure_encryption_time(sys.argv[1])