import unittest
from pin_controller import PinController


class TestPinController(unittest.TestCase):

    def test_pin_controller(self):
        with self.assertRaises(Exception):
            ctrl = PinController()
        with self.assertRaises(Exception):
            ctrl = PinController("some string")
        with self.assertRaises(Exception):
            ctrl = PinController(12.234)
        with self.assertRaises(Exception):
            ctrl = PinController(-12)
        ctrl = PinController(20)
        with self.assertRaises(AssertionError):
            PinController(20, None, up_down="string")


if __name__ == "__main__":
    unittest.main()
