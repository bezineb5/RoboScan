from gpiozero import LED


class Led(LED):
    def __enter__(self) -> "Led":
        self.on()
        return self
    
    def __exit__(self, type, value, traceback):
        self.off()
