import hashlib

ALPHABET = "23456789ABCDEFGHJKMNPQRSTVWXYZ"
DOMAIN_PREFIX = "wcam-confirmation-v1"
CODE_LENGTH = 6
DIGEST_BYTES_USED = 8
GROUP_SIZE = 3


def confirmation_code(nonce: str, phone_fingerprint: str, agent_fingerprint: str) -> str:
    message = "|".join((DOMAIN_PREFIX, nonce, phone_fingerprint, agent_fingerprint))
    digest = hashlib.sha256(message.encode("utf-8")).digest()
    number = int.from_bytes(digest[:DIGEST_BYTES_USED], "big")
    symbols: list[str] = []
    for _ in range(CODE_LENGTH):
        number, remainder = divmod(number, len(ALPHABET))
        symbols.append(ALPHABET[remainder])
    code = "".join(symbols)
    return f"{code[:GROUP_SIZE]}-{code[GROUP_SIZE:]}"
