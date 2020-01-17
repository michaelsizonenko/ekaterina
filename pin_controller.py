import RPi.GPIO as GPIO
import time
from config import logger


class PinController:

    pin = None
    state = 0

    def validate_pin(self, pin):
        if not pin:
            raise Exception("Pin number expected.")
        if not isinstance(pin, str) and not isinstance(pin, int):
            raise Exception("Integer expected")
        if isinstance(pin, str) and not pin.isdigit():
            raise Exception("Integer expected")
        pin = int(pin)
        if pin < 0 or 27 < pin:
            raise Exception("BCM mode provide numbers [0; 27]. {} given.".format(pin))
        return pin

    def callback(self):
        raise NotImplementedError

    def check_pin(self):
        self.handler("Check for {pin} pin".format(pin=self.pin))

    def handler(self, message):
        logger.info(message)
        time.sleep(0.01)
        self.state = GPIO.input(self.pin)
        self.callback(self)

    def gpio_wrapper(self, pin):
        self.handler("Callback handler for pin {pin}".format(pin=pin))

    def __init__(self, pin, callback, up_down=GPIO.PUD_UP, react_on=GPIO.BOTH):
        logger.info("Pin controller for {} pin initiated".format(pin))
        self.pin = self.validate_pin(pin)
        assert (up_down in (GPIO.PUD_UP, GPIO.PUD_DOWN)), \
            "This is weird! Pull-up-down parameter can be either UP or DOWN. {} given".format(up_down)
        self.up_down = up_down
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=self.up_down)
        self.callback = callback
        GPIO.add_event_detect(self.pin, react_on, self.gpio_wrapper, bouncetime=50)



# GPIO.setup(lock_latch_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # pin20 ("язычка")
# GPIO.add_event_detect(lock_latch_pin, GPIO.BOTH, f_lock_latch_pin, bouncetime=50)