import RPi.GPIO as GPIO


class PinController:

    pin = None

    def validate_pin(self, pin):
        if not pin:
            raise Exception("Pin number expected.")
        if not isinstance(pin, str) and not isinstance(pin, int):
            raise Exception("Integer expected")
        if isinstance(pin, str) and not pin.isdigit():
            raise Exception("Integer expected")
        pin = int(pin)
        if pin < 0 or 27 > pin:
            raise Exception("BCM mode provide numbers [0; 27]")
        return pin

    def __init__(self, pin, callback, up_down=GPIO.PUD_UP):
        self.pin = self.validate_pin(pin)
        assert (up_down in GPIO.PUD_UP, GPIO.PUD_DOWN), "This is weird! Pull-up-down parameter can be either UP or DOWN"

