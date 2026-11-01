from datetime import UTC, datetime, timedelta
from ipaddress import IPv4Address
from pathlib import Path

from cryptography import x509

from wcam.network.certificates import VALIDITY, load_or_create_certificate

LAN_IP = IPv4Address("192.168.0.10")
NEW_LAN_IP = IPv4Address("192.168.1.42")
NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)


def test_certificate_is_created_with_lan_ip_in_san(tmp_path: Path) -> None:
    certificate = load_or_create_certificate(tmp_path, LAN_IP, NOW)

    loaded = x509.load_pem_x509_certificate(certificate.certificate_path.read_bytes())
    names = loaded.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert names.get_values_for_type(x509.IPAddress) == [LAN_IP]
    assert certificate.key_path.is_file()


def test_certificate_is_reused_when_ip_matches(tmp_path: Path) -> None:
    first = load_or_create_certificate(tmp_path, LAN_IP, NOW)

    second = load_or_create_certificate(tmp_path, LAN_IP, NOW + timedelta(days=30))

    assert second.fingerprint == first.fingerprint


def test_certificate_is_regenerated_when_ip_changes(tmp_path: Path) -> None:
    first = load_or_create_certificate(tmp_path, LAN_IP, NOW)

    second = load_or_create_certificate(tmp_path, NEW_LAN_IP, NOW)

    assert second.fingerprint != first.fingerprint


def test_certificate_is_regenerated_when_expired(tmp_path: Path) -> None:
    first = load_or_create_certificate(tmp_path, LAN_IP, NOW)

    second = load_or_create_certificate(tmp_path, LAN_IP, NOW + VALIDITY + timedelta(days=1))

    assert second.fingerprint != first.fingerprint


def test_corrupted_certificate_is_regenerated(tmp_path: Path) -> None:
    first = load_or_create_certificate(tmp_path, LAN_IP, NOW)
    first.certificate_path.write_text("not a certificate", encoding="utf-8")

    second = load_or_create_certificate(tmp_path, LAN_IP, NOW)

    assert second.fingerprint != first.fingerprint
