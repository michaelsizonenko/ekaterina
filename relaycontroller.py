import smbus


class RelayController:

    __address = None
    __bus = None

    def __init__(self, address):
        self.__address = address
        self.__bus = smbus.SMBus(1)
        self.__bus.write_byte_data(self.__address, 0x09, 0xff)

    def clear_bit(self, bit):
        value = self.__bus.read_byte(self.__address)
        print("Clear {bit} bit before value {value}".format(value=value, bit=bit))
        value &= ~(1 << bit)
        print("Clear {bit} bit after value {value}".format(value=value, bit=bit))
        self.__bus.write_byte_data(self.__address, 0x09, value)

    def set_bit(self, bit):
        value = self.__bus.read_byte(self.__address)
        print("Set {bit} bit before value {value}".format(value=value, bit=bit))
        value |= 1 << bit
        print("Set {bit} bit after value {value}".format(value=value, bit=bit))
        self.__bus.write_byte_data(self.__address, 0x09, value)

    def toggle_bit(self, bit):
        value = self.__bus.read_byte(self.__address)
        print("Toggle {bit} bit before value {value}".format(value=value, bit=bit))
        value ^= 1 << bit
        print("Toggle {bit} bit after value {value}".format(value=value, bit=bit))
        self.__bus.write_byte_data(self.__address, 0x09, value)

    def check_bit(self, bit):
        value = self.__bus.read_byte(self.__address)
        return (value >> bit) & 1
