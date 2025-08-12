# apps/core/encryption.py
from django.db import models
from cryptography.fernet import Fernet
from django.conf import settings
import base64

class EncryptedField:
    """Helper class for field encryption/decryption"""
    
    @staticmethod
    def get_key():
        key = settings.ENCRYPTION_KEY.encode()
        return base64.urlsafe_b64encode(key.ljust(32)[:32])
        
    @classmethod
    def encrypt(cls, value):
        if not value:
            return value
        f = Fernet(cls.get_key())
        return f.encrypt(str(value).encode()).decode()
    
    @classmethod
    def decrypt(cls, value):
        if not value:
            return value
        f = Fernet(cls.get_key())
        return f.decrypt(value.encode()).decode()

class EncryptedTextField(models.TextField):
    """TextField that encrypts/decrypts values"""
    
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return EncryptedField.decrypt(value)

    def get_prep_value(self, value):
        if value is None:
            return value
        return EncryptedField.encrypt(value)