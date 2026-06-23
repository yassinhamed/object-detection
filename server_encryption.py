#!/usr/bin/env python3
"""
AES Encryption Module for Client
Handles secure encryption of video files using AES-256-CBC
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

class ServerEncryption:
    """Handle AES encryption for video files"""
    
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
    
    def encrypt_file(self, input_path: str, output_path: str = None) -> str:
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        if output_path is None:
            output_path = input_path + ".enc"
        
        iv = os.urandom(self.IV_SIZE)
        
        cipher = Cipher(
            self.ALGORITHM(self.key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        try:
            with open(input_path, 'rb') as infile, open(output_path, 'wb') as outfile:
                outfile.write(iv)
                
                while True:
                    chunk = infile.read(self.CHUNK_SIZE)
                    if not chunk:
                        break
                    
                    if len(chunk) < self.CHUNK_SIZE:
                        padding_length = 16 - (len(chunk) % 16)
                        chunk += bytes([padding_length] * padding_length)
                    
                    encrypted_chunk = encryptor.update(chunk)
                    outfile.write(encrypted_chunk)
                
                final_chunk = encryptor.finalize()
                if final_chunk:
                    outfile.write(final_chunk)
            
            print(f"✅ File encrypted: {input_path} → {output_path}")
            return output_path
            
        except Exception as e:
            if os.path.exists(output_path):
                os.remove(output_path)
            raise RuntimeError(f"Encryption failed: {e}")
    
    def encrypt_file_stream(self, input_path: str) -> bytes:
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        iv = os.urandom(self.IV_SIZE)
        cipher = Cipher(
            self.ALGORITHM(self.key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        encrypted_data = iv
        
        try:
            with open(input_path, 'rb') as f:
                while True:
                    chunk = f.read(self.CHUNK_SIZE)
                    if not chunk:
                        break
                    
                    if len(chunk) < self.CHUNK_SIZE:
                        padding_length = 16 - (len(chunk) % 16)
                        chunk += bytes([padding_length] * padding_length)
                    
                    encrypted_data += encryptor.update(chunk)
                
                final_chunk = encryptor.finalize()
                if final_chunk:
                    encrypted_data += final_chunk
            
            return encrypted_data
        except Exception as e:
            raise RuntimeError(f"Stream encryption failed: {e}")

def encrypt_video(video_path: str, password: str = None) -> str:
    encryptor = ServerEncryption(password)
    return encryptor.encrypt_file(video_path)
