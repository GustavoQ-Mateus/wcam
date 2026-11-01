import socket
from collections.abc import Iterable
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv4Network

import psutil

ROUTE_PROBE_ADDRESS = ("192.0.2.1", 9)
PRIVATE_NETWORKS = (IPv4Network("10.0.0.0/8"), IPv4Network("172.16.0.0/12"), IPv4Network("192.168.0.0/16"))


@dataclass(frozen=True, slots=True)
class LanInterface:
    ip: IPv4Address
    network: IPv4Network


class NoLanInterfaceError(Exception):
    pass


def detect_lan_interface(configured_ip: str | None) -> LanInterface:
    return select_lan_interface(list_ipv4_interfaces(), configured_ip or default_route_ip())


def select_lan_interface(candidates: Iterable[LanInterface], preferred_ip: str | None) -> LanInterface:
    match = next(
        (candidate for candidate in candidates if str(candidate.ip) == preferred_ip and is_lan_address(candidate.ip)),
        None,
    )
    if match is None:
        raise NoLanInterfaceError
    return match


def is_lan_address(ip: IPv4Address) -> bool:
    return any(ip in network for network in PRIVATE_NETWORKS)


def list_ipv4_interfaces() -> list[LanInterface]:
    stats = psutil.net_if_stats()
    interfaces: list[LanInterface] = []
    for name, addresses in psutil.net_if_addrs().items():
        if name in stats and not stats[name].isup:
            continue
        for address in addresses:
            if address.family != socket.AF_INET or not address.netmask:
                continue
            network = IPv4Network(f"{address.address}/{address.netmask}", strict=False)
            interfaces.append(LanInterface(IPv4Address(address.address), network))
    return interfaces


def default_route_ip() -> str | None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect(ROUTE_PROBE_ADDRESS)
        except OSError:
            return None
        local_address: tuple[str, int] = probe.getsockname()
        return local_address[0]
