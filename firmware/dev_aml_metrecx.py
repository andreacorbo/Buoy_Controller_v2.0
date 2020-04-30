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
import utime
from device import DEVICE
import tools.utils as utils
import constants

class METRECX(DEVICE):

    def __init__(self, instance):
        self.instance = instance
        self.config_file = __name__ + "." + constants.CONFIG_TYPE
        DEVICE.__init__(self, self.instance)
        self.timeout = constants.TIMEOUT
        self.prompt = ">"

    def start_up(self):
        """Performs device specific initialization sequence."""
        if self.init_power():
            if self.init_uart():
                if self._break():
                    self._stop_logging()
                    self._set_clock()
                    self._set_sample_rate()
                    self._start_logging()
                    self.off()
                    return True
        return False

    def _timeout(self, start, timeout=None):
        """Checks if a timeout occourred

        Params:
            start(int)
        Returns:
            True or False
        """
        if timeout is None:
            timeout = self.timeout
        if timeout > 0 and utime.time() - start >= timeout:
            return True
        return False

    def _get_reply(self, timeout=None):
        """Returns replies from instrument.

        Returns:
            bytes or None
        """
        start = utime.time()
        while not self._timeout(start, timeout):
            if self.uart.any():
                return self.uart.read().split(b"\r\n")[1].decode("utf-8")
        return

    def _break(self):
        utils.log_file("{} => waiting for instrument getting ready...".format(self.__qualname__))  # DEBUG
        while True:
            self._flush_uart()
            self.uart.write(b"\x03")  # <CTRL+C>
            if self._get_prompt(120):
                return True

    def _get_prompt(self, timeout=None):
        self._flush_uart()
        self.uart.write(b"\r")
        rx = self._get_reply(timeout)
        if rx == self.prompt:
            return True
        else:
            return False

    def _set_date(self):
        """Sets up the instrument date, mm/dd/yy."""
        if self._get_prompt():
            now = utime.localtime()
            self.uart.write("SET DATE {:02d}/{:02d}/{:02d}\r".format(now[1], now[2], int(str(now[0])[:-2])))
            if self._get_reply() == self.prompt:
                return True
        return False

    def _set_time(self):
        """Sets up the instrument time, hh:mm:ss."""
        if self._get_prompt():
            now = utime.localtime()
            self.uart.write("SET TIME {:02d}:{:02d}:{:02d}\r".format(now[3], now[4], now[5]))
            if self._get_reply() ==  self.prompt:
                return True
        return False

    def _get_date(self):
        if self._get_prompt():
            self.uart.write("DISPLAY DATE\r")
            return self._get_reply()[-13:]

    def _get_time(self):
        if self._get_prompt():
            self.uart.write("DISPLAY TIME\r")
            return self._get_reply()[-14:-3]

    def _set_clock(self):
        """Syncs the intrument clock."""
        if self._set_date() and self._set_time():
            utils.log_file("{} => clock synced (dev: {} {} board: {})".format(self.__qualname__, self._get_date(), self._get_time(), utils.time_string(utime.mktime(utime.localtime()))))  # DEBUG
            return True
        utils.log_file("{} => unable to sync clock".format(self.__qualname__))  # DEBUG
        return False

    def _set_sample_rate(self):
        """Sets intrument sampling rate."""
        if self._get_prompt():
            self.uart.write("SET S {:0d} S\r".format(self.config["Sample_Rate"]))
            if self._get_reply() ==  self.prompt:
                self._get_sample_rate()
                return True
        utils.log_file("{} => unable to set sampling rate".format(self.__qualname__))  # DEBUG
        return False

    def _get_sample_rate(self):
        if self._get_prompt():
            self.uart.write("DIS S\r")
            utils.log_file("{} => {}".format(self.__qualname__, self._get_reply()))  # DEBUG

    def _stop_logging(self):
        if self._get_prompt():
            self.uart.write("SET SCAN NOLOGGING\r")
            if self._get_prompt():
                utils.log_file("{} => logging stopped".format(self.__qualname__))  # DEBUG
                return True
        utils.log_file("{} => unable to stop logging".format(self.__qualname__))  # DEBUG
        return False

    def _start_logging(self):
        if self._get_prompt():
            self.uart.write("SET SCAN LOGGING\r")
            if self._get_prompt():
                utils.log_file("{} => logging started".format(self.__qualname__))  # DEBUG
                return True
        utils.log_file("{} => unable to start logging".format(self.__qualname__))  # DEBUG
        return False

    def _format_data(self, sample):
        """Formats data according to output format."""
        epoch = utime.time()
        data = [
            self.config["String_Label"],
            utils.unix_epoch(epoch),
            utils.datestamp(epoch),  # YYMMDD
            utils.timestamp(epoch)  # hhmmss
            ]
        sample = sample.split(self.config["Data_Separator"])
        data.append(",".join(sample[0].split(" ")))
        for field in sample[1:]:
            data.append(field)
        return constants.DATA_SEPARATOR.join(data)

    def main(self):
        """Captures instrument data."""
        if not self.init_uart():
            return
        utils.log_file("{} => acquiring data...".format(self.__qualname__))  # DEBUG
        self.led_on()
        sample = ""
        new_line = False
        start = utime.time()
        while True:
            if utime.time() - start > self.config["Samples"] // self.config["Sample_Rate"]:
                utils.log_file("{} => no data coming from serial".format(self.__qualname__))  # DEBUG
                break
            if self.uart.any():
                byte = self.uart.read(1)
                if byte == b"\n":
                    new_line = True
                elif byte == b"\r" and new_line:
                    break
                elif new_line:
                    sample += byte.decode("utf-8")
        utils.log_data(self._format_data(sample))
        self.led_on()
        return


class UVXCHANGE(DEVICE):

    def __init__(self):
        self.config_file = __name__ + "." + constants.CONFIG_TYPE
        DEVICE.__init__(self)

    def start_up(self):
        """Performs device specific initialization sequence."""
        if self.init_power():
          return True
        return False
