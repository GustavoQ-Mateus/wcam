from wcam.sessions.device import describe_device

ANDROID_CHROME = (
    "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/141.0.0.0 Mobile Safari/537.36"
)
IPHONE_SAFARI = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/18.6 Mobile/15E148 Safari/604.1"
)
SAMSUNG = (
    "Mozilla/5.0 (Linux; Android 14; SM-S921B) AppleWebKit/537.36 (KHTML, like Gecko) "
    "SamsungBrowser/28.0 Chrome/130.0.0.0 Mobile Safari/537.36"
)


def test_device_name_has_system_and_browser() -> None:
    names = [describe_device(agent) for agent in (ANDROID_CHROME, IPHONE_SAFARI, SAMSUNG)]

    assert names == ["Android · Chrome", "iPhone · Safari", "Android · Samsung Internet"]


def test_device_name_omits_unknown_part() -> None:
    assert describe_device("Mozilla/5.0 (Linux; Android 15) SomeBrowser/1.0") == "Android"


def test_device_name_is_none_when_nothing_is_known() -> None:
    assert describe_device("curl/8.11.1") is None
