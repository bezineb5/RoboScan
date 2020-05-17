from gpiozero import OutputDevice


class Led:
    def __init__(self, pin):
        self._led_output = OutputDevice(pin)
    
    def on(self):
        self.state = True

    def off(self):
        self.state = False

    @property
    def state(self):
        return self._led_output.value

    @state.setter
    def state(self, value: bool):
        self._led_output.value = value

    def release(self):
        self.off()
        self._led_output.close()

    def __enter__(self) -> "Led":
        self.on()
        return self
    
    def __exit__(self, type, value, traceback):
        self.off()
