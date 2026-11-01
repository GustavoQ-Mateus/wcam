from ipaddress import IPv4Address, IPv4Network

import pytest

from wcam.network.lan import LanInterface, NoLanInterfaceError, select_lan_interface

LOOPBACK = LanInterface(IPv4Address("127.0.0.1"), IPv4Network("127.0.0.0/8"))
WSL = LanInterface(IPv4Address("172.24.48.1"), IPv4Network("172.24.48.0/20"))
WIFI = LanInterface(IPv4Address("192.168.0.10"), IPv4Network("192.168.0.0/24"))
PUBLIC = LanInterface(IPv4Address("203.0.113.7"), IPv4Network("203.0.113.0/24"))
LINK_LOCAL = LanInterface(IPv4Address("169.254.10.2"), IPv4Network("169.254.0.0/16"))


def test_lan_selects_private_interface_of_default_route() -> None:
    selected = select_lan_interface([LOOPBACK, WSL, WIFI], "192.168.0.10")

    assert selected == WIFI


def test_lan_uses_configured_ip_when_set() -> None:
    selected = select_lan_interface([WIFI, WSL], "172.24.48.1")

    assert selected == WSL


def test_lan_with_unknown_configured_ip_raises() -> None:
    with pytest.raises(NoLanInterfaceError):
        select_lan_interface([WIFI], "10.0.0.5")


def test_lan_without_private_interface_raises() -> None:
    with pytest.raises(NoLanInterfaceError):
        select_lan_interface([LOOPBACK, PUBLIC, LINK_LOCAL], "203.0.113.7")


def test_lan_without_default_route_raises() -> None:
    with pytest.raises(NoLanInterfaceError):
        select_lan_interface([LOOPBACK, WIFI, WSL], None)
