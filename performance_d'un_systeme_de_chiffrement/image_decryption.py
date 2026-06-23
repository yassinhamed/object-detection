#!/usr/bin/env python3
"""
AES-256-CBC Image Decryption Module (PFA-ready)
"""

import os
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


def get_default_password():
    key_path = os.path.join(os.path.dirname(__file__), 'encryption.key')

    if os.path.exists(key_path):
        with open(key_path, 'r') as f:
            pwd = f.read().strip()
            if pwd:
                return pwd

    return os.environ.get("IMAGE_SEC_KEY", "secure_image_key")


class ImageDecryption:

    def __init__(self, password=None):
        self.password = password or get_default_password()
        self.key = self._derive_key(self.password)

    def _derive_key(self, password: str, salt: bytes = b"image_encryption_salt"):
        return hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt,
            100000,
            dklen=32
        )

    def _pkcs7_unpad(self, data: bytes) -> bytes:
        padding_len = data[-1]
        return data[:-padding_len]

    def decrypt_file(self, input_path: str, output_path: str = None):

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"File not found: {input_path}")

        if output_path is None:
            output_path = input_path.replace(".enc", "_decrypted.jpg")

        with open(input_path, 'rb') as f:
            iv = f.read(16)
            ciphertext = f.read()

        cipher = Cipher(
            algorithms.AES(self.key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()

        decrypted_padded = decryptor.update(ciphertext) + decryptor.finalize()

        decrypted = self._pkcs7_unpad(decrypted_padded)

        with open(output_path, 'wb') as f:
            f.write(decrypted)

        print(f"✅ Decryption successful: {output_path}")
        return output_path


# ---------------- MAIN ---------------- #

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python image_decryption.py <encrypted_file>")
        exit(1)

    enc_file = sys.argv[1]

    dec = ImageDecryption()
    dec.decrypt_file(enc_file)