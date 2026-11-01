class FrameGate:
    def __init__(self) -> None:
        self.is_open = False
        self.received = 0
        self.released = 0

    def open(self) -> None:
        self.is_open = True

    def admit(self) -> bool:
        self.received += 1
        if self.is_open:
            self.released += 1
        return self.is_open
