import unittest
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token

class TestSecurity(unittest.TestCase):
    def test_password_hashing_and_verification(self):
        plain = "SuperSecretPassword123"
        hashed = hash_password(plain)
        self.assertNotEqual(plain, hashed)
        self.assertTrue(verify_password(plain, hashed))
        self.assertFalse(verify_password("WrongPassword", hashed))

    def test_jwt_token_creation_and_decoding(self):
        user_id = 42
        token = create_access_token(user_id)
        self.assertIsInstance(token, str)
        decoded_id = decode_access_token(token)
        self.assertEqual(decoded_id, user_id)

    def test_invalid_token_returns_none(self):
        self.assertIsNone(decode_access_token("not-a-valid-token"))

if __name__ == "__main__":
    unittest.main()
