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
import uos
import utime
import uselect
from device import DEVICE
from tools.ymodem import YMODEM
import tools.utils as utils
import constants
import _thread

class MODEM(DEVICE, YMODEM):

    def __init__(self, , *args, **kwargs):
        self.config_file = __name__ + "." + constants.CONFIG_TYPE
        DEVICE.__init__(self, *args, **kwargs)
        self.sending = False
        self.connected = False
        self.sent = False
        self.received = False
        self.timeout = 1
        self.file_paths = []
        self.unsent_files = utils.unsent_files
        self.pre_ats = self.config["Modem"]["Pre_Ats"]
        self.post_ats = self.config["Modem"]["Post_Ats"]
        self.ats_delay = self.config["Modem"]["Ats_Delay"]
        self.call_attempt = self.config["Modem"]["Call_Attempt"]
        self.call_delay = self.config["Modem"]["Call_Delay"]
        self.call_timeout = self.config["Modem"]["Call_Timeout"]
        YMODEM.__init__(self, self._getc, self._putc, mode="Ymodem1k")

    def start_up(self):
        """Performs device specific initialization sequence."""
        #if self.init_power() and self._set_auto_answer():  DEBUG
        if self.init_power():
            return True
        return False

    def _is_ready(self):
        """Waits for modem get ready.

        Returns:
            True or False
        """
        utils.log_file("{} => starting up...".format(__name__), constants.LOG_LEVEL, False)
        for _ in range(constants.TIMEOUT):
            rx_buff = []
            self.uart.write("AT\r")
            t0 = utime.time()
            while True:
                if utime.time() - t0 > 5:  # Waits 5 sec for response.
                    break
                if self.uart.any():
                    byte = self.uart.read(1)
                    if byte == b"\n":
                        continue
                    elif byte == b"\r":
                        rx = "".join(rx_buff)
                        if rx:
                            if rx == "ERROR":
                                break
                            if rx == "OK":
                                return True
                            rx_buff = []
                    else:
                        rx_buff.append(chr(ord(byte)))
            utime.sleep(1)
        utils.log_file("{} => unavailable   ".format(__name__), constants.LOG_LEVEL, True)
        return False

    def _set_auto_answer(self):
        """Initializes modem with auto answer.

        Returns:
            True or False
        """
        if not self._is_ready():
            return False
        else:
            utils.log_file("{} => initialization sequence".format(__name__), constants.LOG_LEVEL, True)
            for at in ["AT\r","AT+CREG=0\r","AT+CBST=7,0,1\r","ATS0=2\r","ATS0?\r"]:
                self.uart.write(at)
                rx_buff = []
                t = utime.time()
                while True:
                    if utime.time() - t == self.call_timeout:
                        print("TIMEOUT OCCURRED")
                        return False
                    if self.uart.any():
                        byte = self.uart.read(1)
                        if byte == b"\n":
                            continue
                        elif byte == b"\r":
                            rx = "".join(rx_buff)
                            if rx:
                                print(rx)
                                if rx == "OK":
                                    break
                                rx_buff = []
                        else:
                            rx_buff.append(chr(ord(byte)))
                utime.sleep(self.ats_delay)
            return True


    def _getc(self, size, timeout=1):
        """Reads bytes from serial.

        Params:
            size(int): num of bytes
            timeout(int)
        Returns:
            given data or None
        """
        r, w, e = uselect.select([self.uart], [], [], timeout)
        if r:
            return self.uart.read(size)
        else:
            return

    def _putc(self, data, timeout=1):
        """Writes bytes to serial.

        Params:
            data(bytes)
            timeout(int)
        Returns:
            written data or None
        """
        r, w, e = uselect.select([], [self.uart], [], timeout)
        if w:
            return self.uart.write(data)
        else:
            return

    def _send(self):
        """Sends files."""
        if self.send(self.unsent_files, constants.TMP_FILE_PFX, constants.SENT_FILE_PFX):
            self.sent = True
            return True
        return False

    def receive(self, attempts):
        """Receives files.

        Params:
            attempts(int): number of attempts
        Returns:
            True or False
        """
        self.uart.write(
        "\r\n"+
        "##################################################\r\n"+
        "#                                                #\r\n"+
        "#              YMODEM RECEIVER V1.1              #\r\n"+
        "#                                                #\r\n"+
        "##################################################\r\n"+
        "WAITING FOR FILES...")
        for counter in range(attempts):
            if self.recv():
                break
        self.uart.write("...RECEIVED\r\n\r\n")
        self.received = True
        return

    def _call(self):
        """Starts a call.

        Returns:
            True or False
        """
        self.uart.read()  # Flushes uart buffer
        for at in self.pre_ats:
            self.uart.write(at)
            rx_buff = []
            now = utime.time()
            while True:
                if utime.time() - now == self.call_timeout:
                    print("TIMEOUT OCCURRED")
                    return False
                if self.uart.any():
                    byte = self.uart.read(1)
                    if byte == b"\n":
                        continue
                    elif byte == b"\r":
                        rx = "".join(rx_buff)
                        if rx:
                            print(rx)
                            if rx == "ERROR":
                                return False
                            if rx == "NO CARRIER":
                                return False
                            if rx == "NO ANSWER":
                                return False
                            if rx == "OK":
                                break
                            elif "CONNECT" in rx:
                                self.uart.read(1)  # Clears last byte \n
                                self.connected = True
                                return True
                            rx_buff = []
                    else:
                        rx_buff.append(chr(ord(byte)))
            utime.sleep(self.ats_delay)

    def _hangup(self):
        """Ends a call.

        Returns:
            True or False
        """
        self.uart.read()  # Flushes uart buffer
        for at in self.post_ats:
            self.uart.write(at)
            rx_buff = []
            now = utime.time()
            while True:
                if utime.time() - now == self.call_timeout:
                    print("TIMEOUT OCCURRED WHILE HANG UP")
                    return False
                if self.uart.any():
                    byte = self.uart.read(1)
                    if byte == b"\n":
                        continue
                    elif byte == b"\r":
                        rx = "".join(rx_buff)
                        if rx:
                            print(rx)
                            if "ERROR" in rx:
                                return False
                            elif "OK" in rx:
                                break
                            rx_buff = []
                            break
                    else:
                        rx_buff.append(chr(ord(byte)))
            utime.sleep(self.ats_delay)
        return True

    def data_transfer(self):
        """Sends files over the gsm network."""
        if not self.init_uart():
            return
        self.sending = True
        self.led_on()
        print("########################################")
        print("#                                      #")
        print("#           YMODEM SENDER V1.1         #")
        print("#                                      #")
        print("########################################")
        self.connected = False
        self.sending = False
        self.sent = False
        error_count = 0
        while True:
            if error_count == int(self.call_attempt):
                utils.log_file("{} => connection unavailable, aborting...".format(self.__qualname__), constants.LOG_LEVEL, True)
                break
            elif not self.connected:
                if not self._call():
                    error_count += 1
                    utime.sleep(self.call_delay)
                    continue
                error_count = 0
            elif not self.sent:
                self._send()
            else:
                if not self._hangup():
                    error_count += 1
                    continue
                break
        self.led_on()
        # self.deinit_uart() DEBUG Restore before deploy???
        return
