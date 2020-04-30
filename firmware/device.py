# The MIT License (MIT)
#
# Copyright (c) 2018 OGS
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import pyb
import utime
import tools.utils as utils
import constants

class DEVICE(object):

    def __init__(self, *args, **kwargs):
        self.instance = args[0]
        self.name = self.__module__ + "." + self.__qualname__ + "_" + self.instance
        self.get_config()
        self.init_uart()
        self.init_gpio()
        self.init_led()

    def get_config(self):
        """Gets the device configuration."""
        try:
            self.config = utils.read_config(self.config_file)[self.__qualname__][self.instance]
            return self.config
        except:
            utils.log_file("{} => unable to load configuration.".format(self.name), constants.LOG_LEVEL)  # DEBUG
            return False

    def init_uart(self):
        """Initializes the uart bus."""
        if "Uart" in self.config:
            try:
                self.uart = pyb.UART(int(constants.UARTS[constants.DEVICES[self.__qualname__ + "_" + self.instance]]), int(self.config["Uart"]["Baudrate"]))
                self.uart.init(int(self.config["Uart"]["Baudrate"]),
                    bits=int(self.config["Uart"]["Bits"]),
                    parity=eval(self.config["Uart"]["Parity"]),
                    stop=int(self.config["Uart"]["Stop"]),
                    timeout=int(self.config["Uart"]["Timeout"]),
                    flow=int(self.config["Uart"]["Flow_Control"]),
                    timeout_char=int(self.config["Uart"]["Timeout_Char"]),
                    read_buf_len=int(self.config["Uart"]["Read_Buf_Len"]))
            except (ValueError) as err:
                utils.log_file("{} => {}.".format(self.name, err), constants.LOG_LEVEL)

    def deinit_uart(self):
        """Deinitializes the uart bus."""
        self.uart.deinit()

    def flush_uart(self):
        """Flushes the uart read buffer."""
        self.uart.read()

    def init_gpio(self):
        """Creates the device pin object."""
        if "Ctrl_Pin" in self.config:
            try:
                self.gpio = pyb.Pin(self.config["Ctrl_Pin"], pyb.Pin.OUT)
            except (ValueError) as err:
                utils.log_file("{} => {}.".format(self.name, err), constants.LOG_LEVEL)

    def init_led(self):
        """Creates the device led object."""
        try:
            self.led = pyb.LED(constants.LEDS["RUN"])
            self.led.off()
        except ValueError as err:
            utils.log_file("{} => {}.".format(self.name, err), constants.LOG_LEVEL)

    def led_on(self):
        """Power on the device led."""
        self.led.on()

    def led_on(self):
        """Power off the device led."""
        self.led.off()

    def init_power(self):
        """Initializes power status at startup."""
        if self.config["Status"] == 1:
            utime.sleep_ms(100)
            self.on()
        else:
            self.off()

    def on(self):
        """Turns on device."""
        if hasattr(self, "gpio"):
            self.gpio.on()  # set pin to off
        utils.status_table[self.name] = 1
        utils.log_file("{} => ON".format(self.name), constants.LOG_LEVEL)  #
        return

    def off(self):
        """Turns off device."""
        if hasattr(self, "gpio"):
            self.gpio.off()  # set pin to off
        utils.status_table[self.name] = 0
        utils.log_file("{} => OFF".format(self.name), constants.LOG_LEVEL)  # DEBUG
        return

    def toggle(self):
        """Toggles the device status between on and off."""
        if hasattr(self, "gpio"):
            if self.gpio.value():
                self.gpio.off()
            else:
                self.gpio.on()
        return

    def status(self, status=None):
        """Returns or sets the current device status."""
        for key, value in constants.DEVICE_STATUS.items():
            if status and value == status.upper():
                utils.status_table[self.name] = key
        return constants.DEVICE_STATUS[utils.status_table[self.name]]
