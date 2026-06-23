#!/usr/bin/env python3
"""
AES Decryption Module for Server
Handles secure decryption of video files using AES-256-CBC
"""

import os
import hashlib
from pathlib import Path
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

def get_default_password() -> str:
    """Get the encryption password from a local key file or environment variable."""
    key_path = os.path.join(os.path.dirname(__file__), 'encryption.key')
    if os.path.exists(key_path):
        with open(key_path, 'r') as f:
            pwd = f.read().strip()
            if pwd:
                return pwd
    return os.environ.get("VIDEO_SEC_KEY", "secure_video_key")

class ClientDecryption:
    """Handle AES decryption for video files"""
    
    # Encryption parameters
    ALGORITHM = algorithms.AES
    KEY_SIZE = 32  # 256 bits for AES-256
    IV_SIZE = 16   # 128 bits for AES IV
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks for memory efficiency
    
    def __init__(self, password: str = None):
        self.password = password or get_default_password()
        self.key = self._derive_key(self.password)
    
    @staticmethod
    def _derive_key(password: str, salt: bytes = b"video_encryption_salt") -> bytes:
        key_material = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt,
            iterations=100000,
            dklen=32  # 256 bits
        )
        return key_material
    
    def decrypt_file(self, input_path: str, output_path: str = None) -> str:
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        if output_path is None:
            output_path = input_path.replace('.enc', '')
        
        try:
            with open(input_path, 'rb') as infile:
                iv = infile.read(self.IV_SIZE)
                
                if len(iv) < self.IV_SIZE:
                    raise ValueError("Invalid encrypted file: IV too short")
                
                cipher = Cipher(
                    self.ALGORITHM(self.key),
                    modes.CBC(iv),
                    backend=default_backend()
                )
                decryptor = cipher.decryptor()
                
                with open(output_path, 'wb') as outfile:
                    while True:
                        chunk = infile.read(self.CHUNK_SIZE)
                        if not chunk:
                            break
                        
                        decrypted_chunk = decryptor.update(chunk)
                        outfile.write(decrypted_chunk)
                    
                    final_chunk = decryptor.finalize()
                    if final_chunk:
                        outfile.write(final_chunk)
                
                with open(output_path, 'r+b') as f:
                    f.seek(-16, 2)
                    last_block = f.read(16)
                    if last_block:
                        padding_length = last_block[-1]
                        if 1 <= padding_length <= 16:
                            if all(b == padding_length for b in last_block[-padding_length:]):
                                f.seek(-padding_length, 2)
                                f.truncate()
            
            print(f"✅ File decrypted: {input_path} → {output_path}")
            return output_path
            
        except Exception as e:
            if os.path.exists(output_path):
                os.remove(output_path)
            raise RuntimeError(f"Decryption failed: {e}")
    
    def decrypt_bytes_stream(self, encrypted_data: bytes) -> bytes:
        if len(encrypted_data) < self.IV_SIZE:
            raise ValueError("Invalid encrypted data: too short")
        
        iv = encrypted_data[:self.IV_SIZE]
        ciphertext = encrypted_data[self.IV_SIZE:]
        
        cipher = Cipher(
            self.ALGORITHM(self.key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        try:
            decrypted_data = decryptor.update(ciphertext) + decryptor.finalize()
            
            padding_length = decrypted_data[-1]
            if 1 <= padding_length <= 16:
                if all(b == padding_length for b in decrypted_data[-padding_length:]):
                    decrypted_data = decrypted_data[:-padding_length]
            
            return decrypted_data
        except Exception as e:
            raise RuntimeError(f"Stream decryption failed: {e}")

def decrypt_video(encrypted_path: str, output_path: str = None, password: str = None) -> str:
    decryptor = ClientDecryption(password)
    return decryptor.decrypt_file(encrypted_path, output_path)
