import time
from image_decryption import ImageDecryption
import sys


def measure_decryption_time(enc_file):

    decryptor = ImageDecryption()

    start_time = time.time()

    output = decryptor.decrypt_file(enc_file)

    end_time = time.time()

    duration = end_time - start_time

    print("\n" + "=" * 50)
    print("⏱️ Decryption Time Analysis")
    print("=" * 50)
    print(f"Input file: {enc_file}")
    print(f"Output file: {output}")
    print(f"Execution time: {duration:.6f} seconds")
    print("=" * 50)

    if duration < 1:
        print("✅ Very fast decryption")
    elif duration < 3:
        print("⚠️ Moderate speed")
    else:
        print("❌ Slow decryption")

    print("=" * 50)


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Usage: python decryption_time.py <encrypted_file>")
        sys.exit(1)

    measure_decryption_time(sys.argv[1])