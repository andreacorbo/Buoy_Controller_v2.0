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
import _thread
import tools.utils as utils
import constants
import tools.inspect as inspect
import sys

class BOARD(object):

    rtc = pyb.RTC()

    devices = {}

    line2uart = {
        1:4,
        3:2,
        7:1,     # attention!!! same as for uart6
        9:5,     # usb
        11:3
        }

    def __init__(self):
        self.config_path  = constants.CONFIG_PATH
        self.config_file = __name__ + "." + constants.CONFIG_TYPE
        self.lastfeed = utime.time()
        self.usb = None
        self.interrupt = None
        self.interrupted = False
        self.escaped = False
        self.prompted = False
        self.interactive = False
        self.connected = False
        self.operational = False
        self.irqs = []
        self.pwr_led()
        self.get_config()
        self.init_devices()
        self.init_interrupts()
        self.disable_interrupts()
        self.init_usb()
        self.init_uart()
        self.input = [self.usb, self.uart]

    def init_led(self):
        for led in constants.LEDS:
            self.led = pyb.LED(constants.LEDS[led]).off()

    def pwr_led(self):
        self.init_led()
        pyb.LED(constants.LEDS["PWR"]).on()

    def sleep_led(self):
        self.init_led()
        pyb.LED(constants.LEDS["SLEEP"]).on()

    def get_config(self):
        """Gets the device configuration."""
        try:
            self.config = utils.read_config(self.config_file)[self.__qualname__]["1"]
            return self.config
        except:
            utils.log_file("{} => unable to load configuration.".format(self.__qualname__), constants.LOG_LEVEL)  # DEBUG
            return False
    def init_usb(self):
        self.usb = pyb.USB_VCP()

    def init_uart(self):
        """Initializes the uart bus."""
        try:
            self.uart = pyb.UART(int(self.config["Uart"]["Bus"]), int(self.config["Uart"]["Baudrate"]))
            self.uart.init(int(self.config["Uart"]["Baudrate"]),
                bits=int(self.config["Uart"]["Bits"]),
                parity=eval(self.config["Uart"]["Parity"]),
                stop=int(self.config["Uart"]["Stop"]),
                timeout=int(self.config["Uart"]["Timeout"]),
                flow=int(self.config["Uart"]["Flow_Control"]),
                timeout_char=int(self.config["Uart"]["Timeout_Char"]),
                read_buf_len=int(self.config["Uart"]["Read_Buf_Len"]))
            return True
        except (ValueError) as err:
            utils.log_file("{} => {}.".format(self.name, err), constants.LOG_LEVEL)
            return False

    def deinit_uart(self):
        """Deinitializes the uart bus."""
        try:
            self.uart.deinit()
        except:
            utils.log_file("{} => unable to deinitialize uart {}".format(self.__qualname__, self.config["Uart"]["Bus"]), constants.LOG_LEVEL)
            return False
        return True

    def set_repl(self):
        if self.line2uart[self.interrupt] == self.config["Uart"]["Bus"]:
            pyb.repl_uart(self.uart)

    def ext_callback(self, line):
        """Sets board to interactive mode"""
        self.disable_interrupts()
        self.interrupt = line
        self.interrupted = True

    def init_interrupts(self):
        """Initializes all external interrupts to wakes up board from sleep mode."""
        for pin in self.config["Irq_Pins"]:
            self.irqs.append(pyb.ExtInt(pyb.Pin(pin[0], pyb.Pin.IN), eval("pyb.ExtInt." + pin[1]), eval("pyb.Pin." + pin[2]), self.ext_callback))

    def enable_interrupts(self):
        """Enables interrupts"""
        self.interrupt = None
        self.interrupted = False
        for irq in self.irqs:
            irq.enable()

    def disable_interrupts(self):
        """Disables interrupts."""
        for irq in self.irqs:
            irq.disable()

    def init_devices(self):
        """ Initializes all configured devices. """
        utils.log_file("Initializing devices...", constants.LOG_LEVEL)
        for file in uos.listdir(constants.CONFIG_PATH):
            f_name = file.split(".")[0]
            f_ext =  file.split(".")[1]
            if f_ext == constants.CONFIG_TYPE:  #  and f_name.split("_")[0] == "dev"
                cfg = utils.read_config(file)
                for key in cfg.keys():
                    for obj in cfg[key]:
                        if cfg[key][obj]["Device"]:
                            try:
                                utils.create_device(f_name + "." + key + "_" + obj, tasks=["start_up"])
                            except ImportError:
                                pass


    def set_mode(self, timeout):
        """ Prints out welcome message. """
        print(
        "##################################################\r\n"+
        "#                                                #\r\n"+
        "#        WELCOME TO PYBUOYCONTROLLER V1.1        #\r\n"+
        "#                                                #\r\n"+
        "##################################################\r\n"+
        "[ESC] INTERACTIVE MODE\r\n"+
        "[DEL] FILE TRANSFER MODE")
        t0 = utime.time()
        while True:
            t1 = utime.time() - t0
            if t1 > timeout:
                break
            print("ENTER YOUR CHOICE WITHIN {} SECS".format(timeout - t1), end="\r")
            r, w, x = uselect.select(self.input, [], [], 0)
            if r:
                byte = r[0].read(1)
                if byte == b"\x1b":  # ESC
                    self.interactive = True
                    print("")
                    return True
                elif byte == b"\x1b[3~":  # DEL
                    self.connected = True
                    print("")
                    return True
        print("")
        return False

    def go_sleep(self, interval):
        """Puts board in sleep mode.

        Params:
            now(int): current timestamp
            wakeup(int): wakeup timestamp
        """
        self.sleep_led()
        self.enable_interrupts()
        remain = constants.WD_TIMEOUT - (utime.time() - self.lastfeed) * 1000
        interval = interval * 1000
        if interval - remain > -3000:
            interval = remain - 3000
        self.rtc.wakeup(interval)  # Set next rtc wakeup (ms).
        pyb.stop()
        self.pwr_led()


class ADC(DEVICE):

    def __init__(self, *args, **kwargs):
        self.config_file = __name__ + "." + constants.CONFIG_TYPE
        DEVICE.__init__(self, *args, **kwargs)
        data_tasks = ["log"]
        if "tasks" in kwargs:
            if any(elem in data_tasks for elem in kwargs["tasks"]):
                if self.main():
                    for task in kwargs["tasks"]:
                        eval("self." + task + "()", {"self":self})
            else:
                for task in kwargs["tasks"]:
                    eval("self." + task + "()", {"self":self})

    def start_up(self):
        """Performs device specific initialization sequence."""
        if self.init_power():
          return True
        return False

    def adcall_mask(self, channels):
        """Creates a mask for the adcall method with the adc's channels to acquire.

        Params:
            channels(dictionary)
        Return:
            mask(hex)
        """
        mask = []
        chs = [16,17,18]  # MCU_TEMP, VREF, VBAT
        chs.extend(channels)
        for i in reversed(range(19)):
            if i in chs:
                mask.append("1")
            else:
                mask.append("0")
        return eval(hex(int("".join(mask), 2)))

    def ad22103(self, vout, vsupply):
        return (vout * 3.3 / vsupply - 0.25) / 0.028

    def battery_level(self, vout):
        return vout * self.config["Adc"]["Channels"]["Battery_Level"]["Calibration_Coeff"]

    def current_level(self, vout):
        return vout * self.config["Adc"]["Channels"]["Current_Level"]["Calibration_Coeff"]

    def main(self):
        """Gets data from internal sensors."""
        utils.log_file("{} => checking up system status...".format(self.name), constants.LOG_LEVEL)
        core_temp = 0
        core_vbat = 0
        core_vref = 0
        vref = 0
        battery_level = 0
        current_level = 0
        ambient_temperature = 0
        self.data = []
        channels = []
        for key in self.config["Adc"]["Channels"].keys():
            channels.append(self.config["Adc"]["Channels"][key]["Ch"])
        adcall = pyb.ADCAll(int(self.config["Adc"]["Bit"]), self.adcall_mask(channels))
        for i in range(int(self.config["Samples"]) * int(self.config["Sample_Rate"])):
            core_temp += adcall.read_core_temp()
            core_vbat += adcall.read_core_vbat()
            core_vref += adcall.read_core_vref()
            vref += adcall.read_vref()
            battery_level += adcall.read_channel(self.config["Adc"]["Channels"]["Battery_Level"]["Ch"])
            current_level += adcall.read_channel(self.config["Adc"]["Channels"]["Current_Level"]["Ch"])
            ambient_temperature += adcall.read_channel(self.config["Adc"]["Channels"]["Ambient_Temperature"]["Ch"])
            i += 1
        core_temp = core_temp / i
        core_vbat = core_vbat / i
        core_vref = core_vref / i
        vref = vref / i
        battery_level = battery_level / i * vref / pow(2, int(self.config["Adc"]["Bit"]))
        current_level = current_level / i * vref / pow(2, int(self.config["Adc"]["Bit"]))
        ambient_temperature = ambient_temperature / i * vref / pow(2, int(self.config["Adc"]["Bit"]))
        battery_level = self.battery_level(battery_level)
        current_level = self.current_level(current_level)
        ambient_temperature = self.ad22103(ambient_temperature, vref)
        epoch = utime.time()
        self.data.append(self.config["String_Label"])
        self.data.append(str(utils.unix_epoch(epoch)))  # unix timestamp
        self.data.append(utils.datestamp(epoch))  # YYMMDD
        self.data.append(utils.timestamp(epoch))  # hhmmss
        self.data.append("{:.4f}".format(battery_level))
        self.data.append("{:.4f}".format(current_level))
        self.data.append("{:.4f}".format(ambient_temperature))
        self.data.append("{:.4f}".format(core_temp))
        self.data.append("{:.4f}".format(core_vbat))
        self.data.append("{:.4f}".format(core_vref))
        self.data.append("{:.4f}".format(vref))
        return True

    def log(self):
        utils.log_data(",".join(map(str, self.data)))
        return
