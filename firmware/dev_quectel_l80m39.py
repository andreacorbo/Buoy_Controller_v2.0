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
from device import DEVICE
from tools.nmea import NMEA
from math import sin, cos, sqrt, atan2, radians

class GPS(DEVICE, NMEA):
    """Creates a GPS object."""

    def __init__(self, *args, **kwargs):
        self.config_file = __name__ + "." + constants.CONFIG_TYPE
        DEVICE.__init__(self, *args, **kwargs)
        NMEA.__init__(self, *args, **kwargs)
        data_tasks = ["log","last_fix","sync_rtc"]
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

    def main(self):
        """Read nmea messages and search for RMC valid strings."""
        utils.log_file("{} => acquiring data...".format(self.name), constants.LOG_LEVEL)
        while True:
            if not self.status() == "READY":
                utils.log_file("{} => timeout occourred".format(self.name), constants.LOG_LEVEL, True)  # DEBUG
                return False
            if self.uart.any():
                if self.get_sentence(self.uart.readchar(), "RMC"):
                    if not self.sentence[2] == "A":
                        utils.log_file("{} => invalid data received".format(self.name), constants.LOG_LEVEL, True)  # DEBUG
                    else:
                        print(self.sentence)
                        return True

    def log(self):
        """Writes out acquired data to file."""
        utils.log_data("$" + ",".join(map(str, self.sentence)))
        return

    def sync_rtc(self):
        """Synchronizes rtc with gps data."""
        if self.is_valid_gprmc():
            utils.log_file("{} => syncyng rtc...".format(self.name), constants.LOG_LEVEL)
            utc_time = self.sentence[1]
            utc_date = self.sentence[9]
            rtc = pyb.RTC()
            try:
                rtc.datetime((int("20"+utc_date[4:6]), int(utc_date[2:4]), int(utc_date[0:2]), 0, int(utc_time[0:2]), int(utc_time[2:4]), int(utc_time[4:6]), float(utc_time[6:])))  # rtc.datetime(yyyy, mm, dd, 0, hh, ii, ss, sss)
                utils.log_file("{} => rtc successfully synchronized (UTC: {})".format(self.name, utils.time_string(utime.time())), constants.LOG_LEVEL)
            except:
                utils.log_file("{} => unable to synchronize rtc".format(self.name, utils.time_string(utime.time())), constants.LOG_LEVEL)
        return

    def last_fix(self):
        """Stores last gps valid position and utc."""
        if self.is_valid_gprmc():
            utils.log_file("{} => saving last gps fix...".format(self.name), constants.LOG_LEVEL)
            utc_time = self.sentence[1]
            utc_date = self.sentence[9]
            lat = "{}{}".format(self.sentence[3], self.sentence[4])
            lon = "{}{}".format(self.sentence[5], self.sentence[6])
            utc = "{}-{}-{} {}:{}:{}".format("20"+utc_date[4:6], utc_date[2:4], utc_date[0:2], utc_time[0:2], utc_time[2:4], utc_time[4:6])
            speed = "{}".format(self.sentence[7])
            heading = "{}".format(self.sentence[8])
            utils.gps = (utc, lat, lon, speed, heading)
            utils.log_file("{} => last fix (UTC: {} POSITION: {} {}, SPEED: {}, HEADING: {})".format(self.name, utc, lat, lon, speed, heading), constants.LOG_LEVEL)  # DEBUG
        return

    def displacement(self):
        # approximate radius of earth in km
        R = 6373.0
        lat1 = radians(utils.gps())
        lon1 = radians(21.0122287)
        lat2 = radians(52.406374)
        lon2 = radians(16.9251681)

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance = R * c

        print("Result:", distance)
        print("Should be:", 278.546, "km")
