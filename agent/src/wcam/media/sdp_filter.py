from ipaddress import IPv4Network

from wcam.network.lan import is_in_network

CANDIDATE_PREFIX = "a=candidate:"
CANDIDATE_ADDRESS_FIELD = 4
FINGERPRINT_PREFIX = "a=fingerprint:sha-256 "
MEDIA_PREFIX = "m="
LINE_BREAK = "\r\n"
REQUIRED_MEDIA = frozenset({"video", "application"})


def keep_candidates_in_network(sdp: str, network: IPv4Network) -> str:
    kept = [line for line in sdp.splitlines() if not is_candidate(line) or candidate_in_network(line, network)]
    return LINE_BREAK.join(kept) + LINE_BREAK


def candidate_addresses(sdp: str) -> list[str]:
    return [address for line in sdp.splitlines() if (address := candidate_address(line)) is not None]


def sha256_fingerprint(sdp: str) -> str | None:
    for line in sdp.splitlines():
        if line.lower().startswith(FINGERPRINT_PREFIX):
            return line[len(FINGERPRINT_PREFIX) :].strip().upper()
    return None


def is_publishable_offer(sdp: str) -> bool:
    return media_kinds(sdp) >= REQUIRED_MEDIA and sha256_fingerprint(sdp) is not None


def media_kinds(sdp: str) -> set[str]:
    return {line[len(MEDIA_PREFIX) :].split(" ", 1)[0] for line in sdp.splitlines() if line.startswith(MEDIA_PREFIX)}


def is_candidate(line: str) -> bool:
    return line.startswith(CANDIDATE_PREFIX)


def candidate_address(line: str) -> str | None:
    if not is_candidate(line):
        return None
    fields = line[len(CANDIDATE_PREFIX) :].split()
    return fields[CANDIDATE_ADDRESS_FIELD] if len(fields) > CANDIDATE_ADDRESS_FIELD else None


def candidate_in_network(line: str, network: IPv4Network) -> bool:
    address = candidate_address(line)
    return address is not None and is_in_network(address, network)
