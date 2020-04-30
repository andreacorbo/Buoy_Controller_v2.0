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
from tools.nmea import NMEA
import tools.utils as utils
import constants
from math import sin, cos, radians, atan2, degrees, pow, sqrt

#define PRESS_CONV_FACT(X) (X*0.075+800.00) //per barometro young modello 61201 VECCHIA !!!!
#define PRESS_CONV_FACT(X) (X*0.125+600.00)   //per barometro young modello 61202V NUOVA !!!!

class METEO(DEVICE, NMEA):

    def __init__(self, *args, **kwargs):
        self.config_file = __name__ + "." + constants.CONFIG_TYPE
        DEVICE.__init__(self, *args, **kwargs)
        NMEA.__init__(self, *args, **kwargs)
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

    def _wd_vect_avg(self, strings):
        """Calculates wind vector average direction.

        Params:
            strings(list)
        Returns:
            avg(float)
        """
        avg = 0
        sample_list = []
        try:
            for sample in strings:
                sample_list.append([int(sample[0])* float(self.config["Meteo"]["Windspeed_"+self.config["Meteo"]["Windspeed_Unit"]]), int(sample[1])/10])
            x = 0
            y = 0
            for sample in sample_list:
                direction = sample[1]
                speed = sample[0]
                x = x + (math.sin(math.radians(direction)) * speed)
                y = y + (math.cos(math.radians(direction)) * speed)
            avg = math.degrees(math.atan2(x, y))
            if avg < 0:
                avg += 360
        except:
            pass
        return avg

    def _ws_vect_avg(self, strings):
        """Calculates wind vector average speed.

        Params:
            strings(list)
        Returns:
            avg(float)
        """
        avg = 0
        sample_list = []
        try:
            for sample in strings:
                sample_list.append([int(sample[0])* float(self.config["Meteo"]["Windspeed_"+self.config["Meteo"]["Windspeed_Unit"]]), int(sample[1])/10])
            x = 0
            y = 0
            for sample in sample_list:
                direction = sample[1]
                speed = sample[0]
                x = x + (math.sin(math.radians(direction)) * math.pow(speed,2))
                y = y + (math.cos(math.radians(direction)) * math.pow(speed,2))
            avg = math.sqrt(x+y) / len(sample_list)
        except:
            pass
        return avg

    def _ws_avg(self, strings):
        """Calculates average wind speed.

        Params:
            strings(list)
        Returns:
            avg(float)
        """
        avg = 0
        sample_list = []
        try:
            for sample in strings:
                sample_list.append(int(sample[0]) * float(self.config["Meteo"]["Windspeed_"+self.config["Meteo"]["Windspeed_Unit"]]))
            avg = sum(sample_list) / len(sample_list)
        except:
            pass
        return avg

    def _ws_max(self, strings):
        """Calculates max wind speed (gust).

        Params:
            strings(list)
        Returns:
            max(float)
        """
        max = 0
        sample_list = []
        try:
            for sample in strings:
                sample_list.append(int(sample[0]) * float(self.config["Meteo"]["Windspeed_"+self.config["Meteo"]["Windspeed_Unit"]]))
            max = max(sample_list)
        except:
            pass
        return max

    def _wd_max(self, strings):
        """Calculates gust direction.

        Params:
            strings(list)
        Returns:
            max(float)
        """
        max = 0
        try:
            for sample in strings:
                if sample[0] == self._ws_max(strings):
                    max = sample[1] / 10
        except:
            pass
        return max

    def _temp_avg(self, strings):
        """Calculates average air temperature.

        Params:
            strings(list)
        Returns:
            avg(float)
        """
        avg = 0
        sample_list = []
        try:
            for sample in strings:
                sample_list.append(int(sample[2]) * float(self.config["Meteo"]["Temp_Conv_0"]) - float(self.config["Meteo"]["Temp_Conv_1"]))
            avg = sum(sample_list) / len(sample_list)
        except:
            pass
        return avg

    def _press_avg(self, strings):
        """Calculates average barometric pressure.

        Params:
            strings(list)
        Returns:
            avg(float)
        """
        avg = 0
        sample_list = []
        try:
            for sample in strings:
                sample_list.append(int(sample[3]) * float(self.config["Meteo"]["Press_Conv_0"]) + float(self.config["Meteo"]["Press_Conv_1"]))
            avg = sum(sample_list) / len(sample_list)
        except:
            pass
        return avg

    def _hum_avg(self, strings):
        """Calculates average relative humidity.

        Params:
            strings(list)
        Returns:
            avg(float)
        """
        avg = 0
        sample_list = []
        try:
            for sample in strings:
                sample_list.append(int(sample[4]) * float(self.config["Meteo"]["Hum_Conv_0"]))
            avg = sum(sample_list) / len(sample_list)
        except:
            pass
        return avg

    def _compass_avg(self, strings):
        """Calculates average heading.

        Params:
            strings(list)
        Returns:
            avg(float)
        """
        avg = 0
        sample_list = []
        try:
            for sample in strings:
                sample_list.append(int(sample[6]) / 10)
            x = 0
            y = 0
            for sample in sample_list:
                x = x + math.sin(math.radians(sample))
                y = y + math.cos(math.radians(sample))
            avg = math.degrees(math.atan2(x, y))
            if avg < 0:
                avg += 360
        except:
            pass
        return avg

    def _radiance_avg(self, strings):
        """Calculates average solar radiance.

        Params:
            strings(list)
        Returns:
            avg(float)
        """
        avg = 0
        sample_list = []
        try:
            for sample in strings:
                sample_list.append(int(sample[5]) * float(self.config["Meteo"]["Rad_Conv_0"]))
            avg = sum(sample_list) / len(sample_list)
        except:
            pass
        return avg

    def main(self):
        """Gets data from weather station

                                       $WIMWV,ddd,a,sss.s,N,A,*hh<CR/LF>
                                          |    |  |   |   | |  |
         NMEA HEADER----------------------|    |  |   |   | |  |
         DIRECTION (0-360 DEGREES)-------------|  |   |   | |  |
         DIRECTION REFERENCE (T)RUE OR (R)ELATIVE-|   |   | |  |
         WIND SPEED (KNOTS)---------------------------|   | |  |
         WIND SPEED UNITS N=KNOTS (NAUTICAL MPH)----------| |  |
         DESIGNATES GOOD DATA-------------------------------|  |
         CHECKSUM FIELD----------------------------------------|

                                       $WIXDR,C,000.0,C,TEMP,H,000,P,%RH,P,0.000,B,BARO,*hh<CR/LF>
         NMEA HEADER----------------------|   |   |   |  |   |  |  |  |  |   |   |  |    |
         TRANSDUCER TYPE = TEMPERATURE--------|   |   |  |   |  |  |  |  |   |   |  |    |
         TEMPERATURE------------------------------|   |  |   |  |  |  |  |   |   |  |    |
         UNITS = CELSIUS------------------------------|  |   |  |  |  |  |   |   |  |    |
         TRANSDUCER ID-----------------------------------|   |  |  |  |  |   |   |  |    |
         TRANSDUCER TYPE = HUMIDITY--------------------------|  |  |  |  |   |   |  |    |
         RELATIVE HUMIDITY--------------------------------------|  |  |  |   |   |  |    |
         UNITS = PERCENT-------------------------------------------|  |  |   |   |  |    |
         TRANSDUCER ID------------------------------------------------|  |   |   |  |    |
         TRANSDUCER TYPE = PRESSURE--------------------------------------|   |   |  |    |
         BAROMETRIC PRESSURE-------------------------------------------------|   |  |    |
         UNITS = BARS------------------------------------------------------------|  |    |
         TRANSDUCER ID--------------------------------------------------------------|    |
         CHECKSUM FIELD------------------------------------------------------------------|

        Returns:
            None
        """
        utils.log_file("{} => acquiring data...".format(self.name), constants.LOG_LEVEL)
        self.led_on()
        string_count = 0
        new_string = False
        string = ""
        strings = []
        self.data = []
        start = utime.time()
        while string_count < self.config["Samples"]:
            if not self.status() == "READY":
                utils.log_file("{} => timeout occourred".format(self.name), constants.LOG_LEVEL, True)  # DEBUG
                return False
            if self.uart.any():
                char = self.uart.readchar()
                if self.config["Data_Format"] == "STRING":
                    if chr(char) == "\n":
                        new_string = True
                    elif chr(char) == "\r":
                        if new_string:
                            strings.append(string.split(self.config["Data_Separator"]))
                            string = ""
                            new_string = False
                            string_count += 1
                    else:
                        if new_string:
                            string = string + chr(char)
                elif self.config["Data_Format"] == "NMEA":
                    self.get_sentence(char)
                    if self.checksum_verified:
                        if self.sentence[0] in self.config["String_To_Acquire"]:
                            if self.sentence[0] == "WIMWV":
                                valid_data = False
                                if self.sentence[5] == "A":
                                    return True
                                else:
                                    utils.log_file("{} => invalid data received".format(self.name), constants.LOG_LEVEL, True)  # DEBUG
        epoch = utime.time()
        self.data.append(self.config["String_Label"])
        self.data.append(utils.unix_epoch(epoch))
        self.data.append(utils.datestamp(epoch))  # YYMMDD
        self.data.append(utils.timestamp(epoch))  # hhmmss
        self.data.append("{:.1f}".format(self._wd_vect_avg(strings)))  # vectorial avg wind direction
        self.data.append("{:.1f}".format(self._ws_avg(strings)))  # avg wind speed
        self.data.append("{:.1f}".format(self._temp_avg(strings)))  # avg temp
        self.data.append("{:.1f}".format(self._press_avg(strings)))  # avg pressure
        self.data.append("{:.1f}".format(self._hum_avg(strings)))  # avg relative humidity
        self.data.append("{:.1f}".format(self._compass_avg(strings)))  # avg heading
        self.data.append("{:.1f}".format(self._ws_vect_avg(strings)))  # vectorial avg wind speed
        self.data.append("{:.1f}".format(self._ws_max(strings)))  # gust speed
        self.data.append("{:.1f}".format(self._wd_max(strings)))  # gust direction
        self.data.append("{:0d}".format(len(strings)))  # number of strings
        self.data.append("{:.1f}".format(self._radiance_avg(strings)))  # solar radiance (optional)
        return True

    def log(self):
        """Writes out acquired data to file."""
        utils.log_data(",".join(map(str, self.data)))
        return
