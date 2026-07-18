"""Password hashing regression tests for the synchronous auth service."""

from services.auth_service import AuthService


def test_bcrypt_password_round_trip():
    service = AuthService()
    password = "tea-pass-123"

    hashed = service.hash_password(password)

    assert hashed.startswith(("$2a$", "$2b$", "$2y$"))
    assert service.verify_password(password, hashed)
    assert not service.verify_password("wrong-password", hashed)


def test_bcrypt_handles_multibyte_password_over_72_bytes_consistently():
    service = AuthService()
    password = "云岫茶坊" * 8

    hashed = service.hash_password(password)

    assert service.verify_password(password, hashed)


def test_verify_password_rejects_malformed_hash():
    assert not AuthService().verify_password("tea-pass-123", "not-a-bcrypt-hash")
