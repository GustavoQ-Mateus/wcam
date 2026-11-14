from collections.abc import Callable

from PIL.Image import Image

class MenuItem:
    def __init__(
        self,
        text: str,
        action: Callable[[], None],
        *,
        enabled: bool = True,
        checked: Callable[[MenuItem], bool] | None = None,
    ) -> None: ...

class Menu:
    SEPARATOR: MenuItem
    def __init__(self, *items: MenuItem) -> None: ...

class Icon:
    icon: Image
    title: str
    menu: Menu
    def __init__(self, name: str, icon: Image) -> None: ...
    def run(self) -> None: ...
    def stop(self) -> None: ...
    def update_menu(self) -> None: ...
