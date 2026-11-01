from wcam.pairing.confirmation_code import confirmation_code

AB = ":".join(["AB"] * 32)
CD = ":".join(["CD"] * 32)


def test_confirmation_code_matches_contract_vectors() -> None:
    codes = [
        confirmation_code("00112233445566778899aabbccddeeff", AB, CD),
        confirmation_code("00112233445566778899aabbccddeeff", CD, AB),
        confirmation_code("ffeeddccbbaa99887766554433221100", AB, CD),
    ]

    assert codes == ["92Q-M2H", "9MX-3B9", "8VG-KBV"]
