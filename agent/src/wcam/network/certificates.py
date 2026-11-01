from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from ipaddress import IPv4Address
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

VALIDITY = timedelta(days=825)
CLOCK_SKEW_ALLOWANCE = timedelta(minutes=5)
COMMON_NAME = "WCam"
TLS_FOLDER = "tls"
CERTIFICATE_FILE = "cert.pem"
KEY_FILE = "key.pem"
PRIVATE_FILE_MODE = 0o600


@dataclass(frozen=True, slots=True)
class TlsCertificate:
    certificate_path: Path
    key_path: Path
    fingerprint: str


def load_or_create_certificate(data_dir: Path, lan_ip: IPv4Address, now: datetime | None = None) -> TlsCertificate:
    moment = now or datetime.now(UTC)
    folder = data_dir / TLS_FOLDER
    certificate_path = folder / CERTIFICATE_FILE
    key_path = folder / KEY_FILE
    certificate = read_certificate(certificate_path, key_path)
    if certificate is None or not is_usable(certificate, lan_ip, moment):
        certificate = create_certificate(certificate_path, key_path, lan_ip, moment)
    return TlsCertificate(certificate_path, key_path, format_fingerprint(certificate))


def read_certificate(certificate_path: Path, key_path: Path) -> x509.Certificate | None:
    if not certificate_path.is_file() or not key_path.is_file():
        return None
    try:
        return x509.load_pem_x509_certificate(certificate_path.read_bytes())
    except ValueError:
        return None


def is_usable(certificate: x509.Certificate, lan_ip: IPv4Address, now: datetime) -> bool:
    if not certificate.not_valid_before_utc <= now < certificate.not_valid_after_utc:
        return False
    try:
        names = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    except x509.ExtensionNotFound:
        return False
    return lan_ip in names.get_values_for_type(x509.IPAddress)


def create_certificate(certificate_path: Path, key_path: Path, lan_ip: IPv4Address, now: datetime) -> x509.Certificate:
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, COMMON_NAME)])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - CLOCK_SKEW_ALLOWANCE)
        .not_valid_after(now + VALIDITY)
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(lan_ip)]), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(key, hashes.SHA256())
    )
    certificate_path.parent.mkdir(parents=True, exist_ok=True)
    write_private_file(
        key_path,
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
    )
    certificate_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    return certificate


def write_private_file(path: Path, content: bytes) -> None:
    path.write_bytes(content)
    path.chmod(PRIVATE_FILE_MODE)


def format_fingerprint(certificate: x509.Certificate) -> str:
    return certificate.fingerprint(hashes.SHA256()).hex(":").upper()
