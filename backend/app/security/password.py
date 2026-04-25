from argon2 import PasswordHasher, exceptions as argon2_exc

# Argon2id defaults (RFC 9106 safe, tuned for server CPU)
_ph = PasswordHasher(
    time_cost=3,
    memory_cost=64 * 1024,   # 64 MiB
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(hash_: str, password: str) -> bool:
    try:
        return _ph.verify(hash_, password)
    except (argon2_exc.VerifyMismatchError, argon2_exc.InvalidHashError, argon2_exc.VerificationError):
        return False


def needs_rehash(hash_: str) -> bool:
    try:
        return _ph.check_needs_rehash(hash_)
    except argon2_exc.InvalidHashError:
        return True
