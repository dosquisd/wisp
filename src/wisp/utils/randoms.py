import random


def get_random_generator() -> random.Random:
    """Return a cryptographically-strong RNG (``random.SystemRandom``)."""
    return random.SystemRandom()


def get_wireguard_port() -> int:
    """Return a random UDP port in the dynamic/private range ``49152-65535``."""
    return get_random_generator().randint(49152, 2**16 - 1)
