import os
import sys
import django
from django.conf import settings

# Setup Django environment
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Mock settings for encryption if not set (for testing purposes only)
# In a real run, we expect these to be in settings or env.
# But since we just added them to settings reading from config/env,
# and we might not have them in the actual env of this agent,
# we might need to inject them if they fail.
# However, let's try to run with what we have first.
# If it fails, we can set them in the script.


def run_tests():
    # Create a temporary config.toml with necessary keys
    import tempfile
    import shutil

    # Create a temp directory to act as BASE_DIR
    temp_dir = tempfile.mkdtemp()
    try:
        # Create config.toml
        config_content = """
[django_settings]
DJANGO_SECRET_KEY = "mock-secret-key-for-testing"
DEBUG = true
ALLOWED_HOSTS = "localhost"
CORS_ALLOWED_ORIGINS = "http://localhost:3000"

[security]
MASTER_KEY = "mock-master-key-32-bytes-base64-encoded="
ENCRYPTION_PEPPER = "mock-pepper"

[DB]
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "password"
POSTGRES_HOST = "localhost"
POSTGRES_PORT = "5432"
POSTGRES_DB = "user-app-template"

[email_settings]
EMAIL_HOST = "localhost"
EMAIL_PORT = 587
EMAIL_USE_TLS = true
EMAIL_HOST_USER = "user"
EMAIL_HOST_PASSWORD = "password"

[project_logging]
PROJECT_LOGS_DIR = "logs"
"""
        with open(os.path.join(temp_dir, 'config.toml'), 'w') as f:
            f.write(config_content)

        # Set BASE_DIR to temp_dir so settings.py picks up our config.toml
        os.environ['BASE_DIR'] = temp_dir

        # Also ensure logs dir exists
        os.makedirs(os.path.join(temp_dir, 'logs'), exist_ok=True)

        # Inject keys for testing if missing (though config.toml should handle it now)
        # We need a valid fernet key for MASTER_KEY
        from cryptography.fernet import Fernet
        valid_master_key = Fernet.generate_key().decode()

        # Update config.toml with valid key
        config_content = config_content.replace(
            'MASTER_KEY = "mock-master-key-32-bytes-base64-encoded="',
            f'MASTER_KEY = "{valid_master_key}"'
        )
        with open(os.path.join(temp_dir, 'config.toml'), 'w') as f:
            f.write(config_content)

        django.setup()

        from utils.encryption import encrypt_value, decrypt_value, generate_blind_index
        from apps.users.models import UserSecret

        print("--- Testing Utilities ---")
        original_text = "sensitive-data-123"

        # Test Encryption
        encrypted = encrypt_value(original_text)
        print(f"Original: {original_text}")
        print(f"Encrypted: {encrypted}")
        assert encrypted != original_text
        assert encrypted is not None

        # Test Decryption
        decrypted = decrypt_value(encrypted)
        print(f"Decrypted: {decrypted}")
        assert decrypted == original_text

        # Test Blind Index
        index1 = generate_blind_index(original_text)
        index2 = generate_blind_index(original_text)
        print(f"Blind Index: {index1}")
        assert index1 == index2
        assert index1 != original_text

        print("\n--- Testing UserSecret Logic ---")
        secret = UserSecret()

        # Test set_sensitive_data for DNI (has index)
        dni_value = "12345678Z"
        secret.set_sensitive_data('dni', dni_value)

        print(f"DNI Encrypted field: {secret.dni_encrypted}")
        print(f"DNI Index field: {secret.dni_index}")

        assert secret.dni_encrypted is not None
        assert secret.dni_index is not None
        assert secret.dni_index == generate_blind_index(dni_value)

        # Test get_sensitive_data
        retrieved_dni = secret.get_sensitive_data('dni')
        print(f"Retrieved DNI: {retrieved_dni}")
        assert retrieved_dni == dni_value

        # Test field without index (e.g. api_secret_binance)
        # Note: In our model update, api_secret_binance_encrypted exists, but api_secret_binance_index does NOT.
        # Let's verify set_sensitive_data handles this gracefully.

        secret_value = "my-super-secret"
        secret.set_sensitive_data('api_secret_binance', secret_value)
        print(f"API Secret Encrypted: {secret.api_secret_binance_encrypted}")

        # Check that it didn't crash and set the value
        assert secret.api_secret_binance_encrypted is not None
        assert decrypt_value(
            secret.api_secret_binance_encrypted) == secret_value

        # Verify no index was set (attribute shouldn't exist or should be untouched if we didn't define it)
        # In the model, api_secret_binance_index is NOT defined.
        # So hasattr check in set_sensitive_data should have returned False.
        assert not hasattr(secret, 'api_secret_binance_index')

        print("\nSUCCESS: All encryption tests passed!")

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    run_tests()
