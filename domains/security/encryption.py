import os
import base64
import logging
import keyring
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

class Encryption:
    """AES-GCM encryption for N.O.V.A's SQLite memory and secrets storage."""
    
    def __init__(self):
        self._key = self.get_or_create_key()
        if self._key:
            self.aesgcm = AESGCM(self._key)
        else:
            self.aesgcm = None

    def get_or_create_key(self) -> bytes:
        """Load the master key from iCloud Keychain, or generate a new one if it doesn't exist."""
        try:
            b64_key = keyring.get_password("nova", "master_key")
            if b64_key:
                return base64.b64decode(b64_key)
            
            logger.info("Generating new master AES-GCM encryption key...")
            new_key = os.urandom(32)
            keyring.set_password("nova", "master_key", base64.b64encode(new_key).decode('utf-8'))
            return new_key
            
        except Exception as e:
            logger.warning(f"CRITICAL: Keyring cannot access macOS Keychain. Memory will NOT be encrypted properly: {e}")
            return None

    def encrypt(self, plaintext: str) -> str:
        """Encrypts a plaintext string using AES-GCM and returns a base64 encoded payload."""
        if not self.aesgcm:
            logger.error("Encryption requested but no master key is loaded.")
            return ""
            
        nonce = os.urandom(12)
        
        # cryptography's AESGCM encrypt() returns the ciphertext and 16-byte authentication tag concatenated
        ciphertext_and_tag = self.aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        
        # Payload shape: [12 bytes nonce] + [ciphertext] + [16 bytes tag]
        payload = nonce + ciphertext_and_tag
        return base64.b64encode(payload).decode('utf-8')

    def decrypt(self, ciphertext_b64: str) -> str:
        """Decrypts a base64 encoded payload using AES-GCM."""
        if not self.aesgcm:
            logger.error("Decryption requested but no master key is loaded.")
            return ""
            
        try:
            payload = base64.b64decode(ciphertext_b64)
            nonce = payload[:12]
            ciphertext_and_tag = payload[12:]
            
            plaintext_bytes = self.aesgcm.decrypt(nonce, ciphertext_and_tag, None)
            return plaintext_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to decrypt payload (possible tampering or incorrect key): {e}")
            return ""

    def store_secret(self, name: str, value: str):
        """Encrypt a value and store it securely in the Keychain."""
        encrypted = self.encrypt(value)
        if encrypted:
            try:
                keyring.set_password("nova_secrets", name, encrypted)
            except Exception as e:
                logger.warning(f"Failed to store secret '{name}' in macOS Keychain: {e}")

    def get_secret(self, name: str) -> str:
        """Retrieve and decrypt an encrypted secret from the Keychain."""
        try:
            encrypted = keyring.get_password("nova_secrets", name)
            if not encrypted:
                return ""
            return self.decrypt(encrypted)
        except Exception as e:
            logger.warning(f"Failed to retrieve secret '{name}' from macOS Keychain: {e}")
            return ""

    def encrypt_db_field(self, value: str) -> str:
        """Thin wrapper for memory_store encryption hooks."""
        if not value:
            return ""
        return self.encrypt(value)

    def decrypt_db_field(self, value: str) -> str:
        """Thin wrapper for memory_store decryption hooks."""
        if not value:
            return ""
        return self.decrypt(value)

# Export singleton
encryption = Encryption()
