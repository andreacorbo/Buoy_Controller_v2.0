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

ESC_CHAR = "#"
THREAD_TIMEOUT = 60  # sec.
TIMEOUT = 60  # sec.
SESSION_TIMEOUT = 604800  # sec.
LOGIN_ATTEMPTS = 3
PASSWD = "pippo"
WD_TIMEOUT = 30000  # 1000ms < watchdog timer timeout < 32000ms
MEDIA = ["/sd", "/flash"]
STORAGE = ""
CONFIG_PATH = "config"
CONFIG_TYPE = "json"
LOG_PATH = "log"
DATA_DIR = "data"
DATA_FILE_NAME = "\"{:04d}{:02d}{:02d}\".format(utime.localtime()[0], utime.localtime()[1], utime.localtime()[2])"
TMP_FILE_PFX = "$"
SENT_FILE_PFX = "_"
BUF_DAYS = 3
DATA_SEPARATOR = ","
LOG_LEVEL = 0  # 0 screen output, 1 log to file
VERBOSE = 0  # 0 nothing, 1 shows device activity
DEVICE_STATUS = {0:"OFF", 1:"ON", 2:"READY"}
LEDS = {"IO":1, "PWR":2, "RUN":3, "SLEEP":4}  # red, green, yellow, blue
UARTS = {1:2, 2:4, 3:6, 4:1}
DEVICES = {"GPS_1":1, "METEO_1":1, "METRECX_1":2, "ADCP_1":3}
DATA_ACQUISITION_INTERVAL = 60  # sec.
SCHEDULER = {"GPS_1":{"sync_rtc":120, "last_fix":30}}
