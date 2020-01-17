import RPi.GPIO as GPIO
import time
from config import system_config, logger


class PinFactory:
    pass


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
        self.handler(self.pin)

    def handler(self, pin):
        time.sleep(0.01)
        self.state = GPIO.input(self.pin)
        self.callback(self)          

    def __init__(self, pin, callback, up_down=GPIO.PUD_UP, react_on=GPIO.BOTH):
        logger.info("Pin controller for {} pin initiated".format(pin))
        self.pin = self.validate_pin(pin)
        assert (up_down in (GPIO.PUD_UP, GPIO.PUD_DOWN)), \
            "This is weird! Pull-up-down parameter can be either UP or DOWN. {} given".format(up_down)
        self.up_down = up_down
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=self.up_down)
        self.callback = callback
        GPIO.add_event_detect(self.pin, react_on, self.handler, bouncetime=50)



# # pin#26 callback (проверка сработки внут защелки (ригеля) на закрытие)
# def f_lock_door_from_inside_pin(pin):
#     time.sleep(0.01)
#     global doors_lock_pin26_state, close_door_from_inside_counter
#     doors_lock_pin26_state = GPIO.input(pin)
#     if not doors_lock_pin26_state:
#         time.sleep(0.01)
#         doors_lock_pin26_state = GPIO.input(pin)
#         if not doors_lock_pin26_state:
#             relay2_controller.set_bit(6)  # зажигаем красный светодиод
#             logger.info("Callback for {pin} pin. The door has been locked from inside. Counter : {counter}"
#                         .format(pin=pin, counter=close_door_from_inside_counter))
#             close_door_from_inside_counter = close_door_from_inside_counter + 1
#     #            return
#     time.sleep(0.01)
#     if doors_lock_pin26_state:
#         relay2_controller.clear_bit(6)  # тушим красный светодиод

# GPIO.setup(doors_lock_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # pin26 (внут защелка (ригель))
# GPIO.add_event_detect(doors_lock_pin, GPIO.BOTH, f_lock_door_from_inside_pin,
#                       bouncetime=50)  # pin26 (внут защелки (ригеля))