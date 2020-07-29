import time

from gpiozero import OutputDevice


class StepperMotor:
    __slots__ = ['_coil_A_1_pin', '_coil_A_2_pin', '_coil_B_1_pin', '_coil_B_2_pin', ]

    # This is comming from: http://www.raspberrypi-spy.co.uk/2012/07/stepper-motor-control-in-python/    
    _seq = [[1,0,0,1],
            [1,0,0,0],
            [1,1,0,0],
            [0,1,0,0],
            [0,1,1,0],
            [0,0,1,0],
            [0,0,1,1],
            [0,0,0,1]]

    def __init__(self, coil_A_1_pin: int, coil_A_2_pin: int, coil_B_1_pin: int, coil_B_2_pin: int) -> None:
        self._coil_A_1_pin = OutputDevice(coil_A_1_pin)
        self._coil_A_2_pin = OutputDevice(coil_A_2_pin)
        self._coil_B_1_pin = OutputDevice(coil_B_1_pin)
        self._coil_B_2_pin = OutputDevice(coil_B_2_pin)

    def rotate(self, delay: float, steps: int) -> None:
        if steps >= 0:
            self.forward(delay, steps)
        else:
            self.backwards(delay, abs(steps))

    def forward(self, delay: float, steps: int) -> None:
        for i in range(steps):
            for pattern in self._seq:
                self._set_step(*pattern)
                time.sleep(delay)
 
    def backwards(self, delay: float, steps: int) -> None:  
        for i in range(steps):
            for pattern in reversed(self._seq):
                self._set_step(*pattern)
                time.sleep(delay)
    
    def stop(self) -> None:
        self._set_step(0, 0, 0, 0)

    def release(self) -> None:
        self.stop()
        self._coil_A_1_pin.close()
        self._coil_A_2_pin.close()
        self._coil_B_1_pin.close()
        self._coil_B_2_pin.close()

    def _set_step(self, w1: int, w2: int, w3: int, w4: int) -> None:
        self._coil_A_1_pin.value = w1
        self._coil_A_2_pin.value = w2
        self._coil_B_1_pin.value = w3
        self._coil_B_2_pin.value = w4

    def __enter__(self) -> "StepperMotor":
        return self

    def __exit__(self, type, value, traceback):
        self.release()
