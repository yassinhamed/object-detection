#!/usr/bin/env python3
"""
AES-256-CBC Image Encryption Module (Correct Version)
PFA-ready implementation with proper PKCS7 padding
"""

import os
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


def get_default_password() -> str:
    """Load encryption key from file or environment variable."""
    key_path = os.path.join(os.path.dirname(__file__), 'encryption.key')

    if os.path.exists(key_path):
        with open(key_path, 'r') as f:
            pwd = f.read().strip()
            if pwd:
                return pwd

    return os.environ.get("IMAGE_SEC_KEY", "secure_image_key")


class ImageEncryption:
    """AES-256-CBC encryption for image/video files"""

    KEY_SIZE = 32   # 256-bit key
    IV_SIZE = 16    # 128-bit IV (AES block size)

    def __init__(self, password: str = None):
        self.password = password or get_default_password()
        self.key = self._derive_key(self.password)

    @staticmethod
    def _derive_key(password: str, salt: bytes = b"image_encryption_salt") -> bytes:
        """Derive AES key using PBKDF2"""
        return hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt,
            100000,
            dklen=32
        )

    def _pkcs7_pad(self, data: bytes) -> bytes:
        """Apply PKCS7 padding (correct AES standard)"""
        padding_len = 16 - (len(data) % 16)
        return data + bytes([padding_len] * padding_len)

    def encrypt_file(self, input_path: str, output_path: str = None) -> str:
        """Encrypt file using AES-256-CBC"""

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"File not found: {input_path}")

        if output_path is None:
            output_path = input_path + ".enc"

        iv = os.urandom(self.IV_SIZE)

        cipher = Cipher(
            algorithms.AES(self.key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()

        try:
            with open(input_path, 'rb') as infile:
                data = infile.read()

            # ✅ Correct padding (ONLY ONCE)
            padded_data = self._pkcs7_pad(data)

            encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

            with open(output_path, 'wb') as outfile:
                outfile.write(iv)              # store IV first
                outfile.write(encrypted_data)  # then ciphertext

            print(f"✅ Encryption successful: {input_path} → {output_path}")
            return output_path

        except Exception as e:
            if os.path.exists(output_path):
                os.remove(output_path)
            raise RuntimeError(f"Encryption failed: {e}")

    def encrypt_bytes(self, input_path: str) -> bytes:
        """Return encrypted data in memory (IV + ciphertext)"""

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"File not found: {input_path}")

        iv = os.urandom(self.IV_SIZE)

        cipher = Cipher(
            algorithms.AES(self.key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()

        with open(input_path, 'rb') as infile:
            data = infile.read()

        padded_data = self._pkcs7_pad(data)
        encrypted = encryptor.update(padded_data) + encryptor.finalize()

        return iv + encrypted


# ---------------- MAIN ---------------- #

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python image_encryption.py <input_file> [output_file] [password]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    password = sys.argv[3] if len(sys.argv) > 3 else None

    enc = ImageEncryption(password)
    enc.encrypt_file(input_file, output_file)