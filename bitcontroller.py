class BitController:
    __value = 0

    def get_value(self):
        return self.__value

    def __init__(self, value=0):
        self.__value = value

    def set_bit(self, n):
        self.__value |= 1 << n

    def clear_bit(self, n):
        self.__value &= ~(1 << n)

    def toggle_bit(self, n):
        self.__value ^= 1 << n

    def check_bit(self, n):
        bit = (self.__value >> n) & 1
        return bit
