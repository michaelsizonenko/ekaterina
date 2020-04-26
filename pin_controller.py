import RPi.GPIO as GPIO
import time
import asyncio
from config import logger


class PinController:

    pin = None
    state = 0
    loop = None

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

    def callback(self, data):
        pass

    def before_callback(self, data):
        pass

    def check_pin(self):
        self.handler("Check for {pin} pin".format(pin=self.pin))
        
    def check_event(self):
        return (not self.state and self.up_down == GPIO.PUD_UP) or (self.state and self.up_down == GPIO.PUD_DOWN)

    def handler(self, message):
        time.sleep(0.02)
        self.state = GPIO.input(self.pin)
        self.before_callback(self)
        if self.check_event():
            time.sleep(0.02)
            self.state = GPIO.input(self.pin)
            if self.check_event():
                logger.info(message)
                asyncio.run_coroutine_threadsafe(self.callback(), self.loop)
                # self.callback(self)

    def gpio_wrapper(self, pin):
        print("GPIO wrapper handler {}".format(pin))
        self.handler("Callback handler for pin {pin}".format(pin=pin))

    def __init__(self, loop, pin, callback, up_down=GPIO.PUD_UP, react_on=GPIO.BOTH, before_callback=None):
        logger.info("Pin controller for {} pin has been initiated".format(pin))
        if loop is None:
            raise Exception("Unexpected value for loop")
        self.loop = loop
        self.pin = self.validate_pin(pin)
        assert (up_down in (GPIO.PUD_UP, GPIO.PUD_DOWN)), \
            "This is weird! Pull-up-down parameter can be either UP or DOWN. {} given".format(up_down)
        self.up_down = up_down
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=self.up_down)
        self.callback = callback
        if before_callback:
            self.before_callback = before_callback
        GPIO.add_event_detect(self.pin, react_on, self.gpio_wrapper, bouncetime=200)
        logger.info(self.__dict__)
