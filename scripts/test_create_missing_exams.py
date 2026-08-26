import unittest
from unittest.mock import patch

import create_missing_exams


class AuthConfigTests(unittest.TestCase):
    def test_accepts_production_and_test_endpoints(self):
        cases = (
            "https://quizforge.ai",
            "https://qftest.sntrace.dev",
            "http://localhost:5003",
            "http://127.0.0.1:5003",
        )

        for base_url in cases:
            with self.subTest(base_url=base_url), \
                 patch.object(create_missing_exams, "BASE_URL", base_url), \
                 patch.object(create_missing_exams, "LOGIN_EMAIL", "automation@example.com"), \
                 patch.object(create_missing_exams, "LOGIN_PASSWORD", "secret"):
                create_missing_exams.validate_auth_config()

    def test_rejects_untrusted_credential_destination(self):
        with patch.object(create_missing_exams, "BASE_URL", "https://example.com"), \
             patch.object(create_missing_exams, "LOGIN_EMAIL", "automation@example.com"), \
             patch.object(create_missing_exams, "LOGIN_PASSWORD", "secret"), \
             self.assertRaises(SystemExit):
            create_missing_exams.validate_auth_config()

    def test_rejects_credentials_embedded_in_url(self):
        with patch.object(create_missing_exams, "BASE_URL", "https://user:pass@quizforge.ai"), \
             patch.object(create_missing_exams, "LOGIN_EMAIL", "automation@example.com"), \
             patch.object(create_missing_exams, "LOGIN_PASSWORD", "secret"), \
             self.assertRaises(SystemExit):
            create_missing_exams.validate_auth_config()

    def test_requires_both_credentials(self):
        with patch.object(create_missing_exams, "BASE_URL", "https://quizforge.ai"), \
             patch.object(create_missing_exams, "LOGIN_EMAIL", None), \
             patch.object(create_missing_exams, "LOGIN_PASSWORD", None), \
             self.assertRaises(SystemExit):
            create_missing_exams.validate_auth_config()


if __name__ == "__main__":
    unittest.main()
