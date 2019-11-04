import unittest
from bitcontroller import BitController


class TestPyBit(unittest.TestCase):

    def setUp(self):
        self.controller = BitController()

    def test_set_bit(self):
        self.controller.set_bit(0)
        self.assertEqual(self.controller.get_value(), 1)
        self.controller.set_bit(1)
        self.assertEqual(self.controller.get_value(), 3)
        self.controller.set_bit(2)
        self.assertEqual(self.controller.get_value(), 7)
        self.controller.clear_bit(2)
        self.assertEqual(self.controller.get_value(), 3)
        self.controller.clear_bit(1)
        self.assertEqual(self.controller.get_value(), 1)
        self.controller.clear_bit(0)
        self.assertEqual(self.controller.get_value(), 0)
        self.controller.toggle_bit(7)
        self.assertEqual(self.controller.get_value(), 128)
        self.assertEqual(1, self.controller.check_bit(7))
        self.controller.toggle_bit(7)
        self.assertEqual(self.controller.get_value(), 0)
        self.assertEqual(0, self.controller.check_bit(7))


if __name__ == '__main__':
    unittest.main()
