import time

import pytest

from ploutos.core.exceptions import AuthError
from ploutos.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_and_verify():
    plain = "super-secret"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)


def test_verify_wrong_password():
    hashed = hash_password("correct")
    assert not verify_password("wrong", hashed)


def test_access_token_decode():
    data = {"sub": "user-id", "role": "user"}
    token = create_access_token(data)
    payload = decode_token(token, expected_type="access")
    assert payload.sub == "user-id"
    assert payload.role == "user"


def test_refresh_token_decode():
    data = {"sub": "user-id", "role": "admin"}
    token = create_refresh_token(data)
    payload = decode_token(token, expected_type="refresh")
    assert payload.sub == "user-id"


def test_wrong_token_type_raises():
    token = create_access_token({"sub": "x", "role": "user"})
    with pytest.raises(AuthError, match="Invalid token type"):
        decode_token(token, expected_type="refresh")


def test_invalid_token_raises():
    with pytest.raises(AuthError, match="Invalid token"):
        decode_token("not.a.token")
