import random


def get_random_generator() -> random.Random:
    return random.SystemRandom()


def get_wireguard_port() -> int:
    return get_random_generator().randint(49152, 2**16 - 1)
