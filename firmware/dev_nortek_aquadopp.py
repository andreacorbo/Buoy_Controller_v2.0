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
import ubinascii
import math

class ADCP(DEVICE):

    modes = {
        b"\x00\x00":"Firmware upgrade",
        b"\x01\x00":"Measurement",
        b"\x02\x00":"Command",
        b"\x04\x00":"Data retreival",
        b"\x05\x00":"Confirmation",
        b"\x0a\x0d\x43\x6f\x6e\x66\x69\x72\x6d\x3a":"Confirmation"
        }

    coord_system = {
        0:"ENU",
        1:"XYZ",
        2:"BEAM"
        }

    head_cfg = ("Pressure sensor", "Magnetometer sensor", "Tilt sensor")

    hw_cfg = ("Recorder installed", "Compass installed")

    def __init__(self, instance):
        self.instance = instance
        self.config_file = __name__ + "." + constants.CONFIG_TYPE
        DEVICE.__init__(self, self.instance)
        self.timeout = self.config["Timeout"]
        self.usr_cfg = ()
        self.hw_cfg = ()
        self.head_cfg = ()

    def start_up(self):
        """Performs device specific initialization sequence."""
        if self.init_power():
            utime.sleep_ms(500)  # DEBUG Allows instrument to start properly prior to send commands
            if self.init_uart():
                self._set_clock()
                self._set_usr_cfg()
                if self._get_cfg():
                    self._parse_cfg()
                self._start_delayed()
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
        while True:
            if self._timeout(start, timeout):
                return
            if self.uart.any():
                x = self.uart.read()
                return x

    def _ack(self, rx):
        """Parses acknowledge bytes sequence.

        Params:
            reply(bytes)
        Returns:
            True or False
        """
        if rx:
            if rx[-2:] == b"\x06\x06":
                utils.verbose("<= ACK", constants.VERBOSE)
                return True
            elif rx[-2:] == b"\x15\x15":
                utils.verbose("<= NAK", constants.VERBOSE)
                return False
        return

    def cmd_iface(self, cmd):
        """Command interface.
        Sends commands to instrument.

        Params:
            cmd(bytes)
        Returns:
            None
        """
        if cmd == b"":
            self._break()
        elif cmd == b"\x3F":
            self._get_cmd_list()
        elif cmd == b"SR":
            self._start_measurement()
        else:
            self.uart.write(cmd)
            return

    def data_iface(self, reply, cmd=None):
        """Data interface.
        Parse instrument replies.

        Params:
            reply(bytes)
            cmd(bytes)
        Returns:
            True or False
        """
        if self._ack(reply):
            try:
                reply = eval("self._" + cmd.decode("ascii").lower() + "(reply)", {"self": self, "reply": reply})
            except:
                print("NO COMMAND SPECIFIC DATA PARSING METHOD DEFINED")
            print(reply)
            return True
        elif reply.count(b"\x15") < 3:
            return True
        return False

    def _get_mode(self):
        """Gets current instrument mode."""
        utils.verbose("=> II", constants.VERBOSE)
        self.uart.write("II")
        rx = self._get_reply()
        if self._ack(rx):
            return self.modes[rx[:-2]]
        return

    def _break(self):
        """Sends break to instrument."""
        utils.verbose("=> @@@@@@K1W%!Q", constants.VERBOSE)
        self.uart.write("@@@@@@")
        utime.sleep_ms(100)
        self.uart.write("K1W%!Q")
        start = utime.time()
        while True:
            if self._timeout(start):
                return False
            rx = self._get_reply()
            if self._ack(rx):
                if b"\x0a\x0d\x43\x6f\x6e\x66\x69\x72\x6d\x3a" in rx:
                    self._confirm()
                else:
                    utils.verbose(rx, constants.VERBOSE)
                    return True

    def _confirm(self):
        """Enters command mode

        Preceded by a break command, this command is sent to force the
        instrument to exit Measurement mode and enter Command
        mode.

        Returns:
            true or False
        """
        utils.verbose("=> MC", constants.VERBOSE)
        self.uart.write("MC")
        rx = self._get_reply()
        if self._ack(rx):
            return True
        return False

    def _calc_checksum(self, reply):
        """Computes data checksum: b58c(hex) + sum of all words in structure.

        Params:
            reply(bytes)
        """
        sum=0
        j=0
        for i in range(int.from_bytes(reply[2:4], "little")-1):
            sum += int.from_bytes(reply[j:j+2], "little")
            j = j+2
        return (int.from_bytes(b"\xb5\x8c", "big") + sum) % 65536

    def verify_checksum(self, reply):
        """Verifies data checksum.

        Params:
            reply(bytes)
        Returns:
            True or False
        """
        checksum = int.from_bytes(reply[-2:], "little")
        calc_checksum = self._calc_checksum(reply)
        if checksum == calc_checksum:
            return True
        utils.verbose("checksum {} calc_checksum {}".format(checksum, calc_checksum), constants.VERBOSE)  # DEBUG
        return False

    def _get_cfg(self):
        """Reads complete configuration data

        Reads the currently used hardware configuration, the head
        configuration, and the deployment configuration from the
        instrument.
        """
        start = utime.time()
        while True:
            if self._timeout(start):
                break
            if self._break():
                utils.verbose("=> GA", constants.VERBOSE)
                self.uart.write("GA")
                rx = self._get_reply()
                if self._ack(rx) and self.verify_checksum(rx[0:48]) and self.verify_checksum(rx[48:272]) and self.verify_checksum(rx[272:784]):
                    try:
                        with open("config/adcp.cfg", "wb") as cfg:
                            cfg.write(rx)
                            utils.log_file("{} => retreived instrument config".format(self.__qualname__))  # DEBUG
                            return True
                    except:
                        break
        utils.log_file("{} => unable to retreive instrument config".format(self.__qualname__))  # DEBUG
        return False

    def _parse_cfg(self):
        """Parses configuration data."""
        try:
            with open("config/adcp.cfg", "rb") as cfg:
                bytes = cfg.read()
                self.hw_cfg = self._parse_hw_cfg(bytes[0:48])         # Hardware config (48 bytes)
                self.head_cfg = self._parse_head_cfg(bytes[48:272])   # Head config (224 bytes)
                self.usr_cfg = self._parse_usr_cfg(bytes[272:784])    # Deployment config (512 bytes)
            utils.log_file("{} => parsed instrument config".format(self.__qualname__))  # DEBUG
            return True
        except:
            utils.log_file("{} => unable to parse instrument config".format(self.__qualname__))  # DEBUG
            return False


    def _get_hw_cfg(self):
        """Reads the current hardware configuration from the instrument."""
        start = utime.time()
        while True:
            if self._timeout(start):
                utils.log_file("{} => unable to retreive hardware config".format(self.__qualname__))  # DEBUG
                return False
            if self._break():
                vebose("=> GP", constants.VERBOSE)
                self.uart.write("GP")
                rx = self._get_reply()
                if self._ack(rx):
                    if self.verify_checksum(rx[:-2]):
                        self.hw_cfg = self._parse_hw_cfg(rx)
                        utils.log_file("{} => retreived hardware config".format(self.__qualname__))  # DEBUG
                        return True

    def _parse_hw_cfg(self, reply):
        """Parses the hardware configuration

        Params:
            reply(bytes)
        Returns:
            string
        """
        return (
            "{:02x}".format(reply[0]),                                         # [0] Sync
            "{:02x}".format(int.from_bytes(reply[1:2], "little")),             # [1] Id
            int.from_bytes(reply[2:4], "little"),                              # [2] Size
            reply[4:18].decode("ascii"),                                       # [3] SerialNo
            self._decode_hw_cfg(int.from_bytes(reply[18:20], "little")),       # [4] Config
            int.from_bytes(reply[20:22], "little"),                            # [5] Frequency
            reply[22:24],                                                      # [6] PICVersion
            int.from_bytes(reply[24:26], "little"),                            # [7] HWRevision
            int.from_bytes(reply[26:28], "little"),                            # [8] RecSize
            self._decode_hw_status(int.from_bytes(reply[28:30], "little")),    # [9] Status
            reply[30:42],                                                      # [10] Spare
            reply[42:46].decode("ascii")                                       # [11] FWVersion
            )

    def _decode_hw_cfg(self, cfg):
        """Decodes hardware constants."""
        return (
            "RECORDER {}".format("NO" if cfg >> 0 & 1  else "YES"),
            "COMPASS {}".format("NO" if cfg >> 1 & 1  else "YES")
            )

    def _decode_hw_status(self, status):
        """Decodes hardware status."""
        return "VELOCITY RANGE {}".format("HIGH" if status >> 0 & 1  else "NORMAL")

    def _set_usr_cfg(self):
        """Uploads a deployment config to the instrument and sets up the device
        Activation_Rate and Warmup_Duration parameters according to the current
        deployment constants."""
        start = utime.time()
        while True:
            if self._timeout(start):
                break
            if self._break():
                try:
                    with open(self.config["Adcp"]["Deployment_Config"], "rb") as pdc:
                        cfg = pdc.read()
                        rate = int.from_bytes(cfg[38:40], "little")
                        self.config["Activation_Rate"] = rate
                        self.config["Warmup_Duration"] = rate - self.config["Samples"]
                        usr_cfg = cfg[0:48] + self._set_start() + cfg[54:510]
                        checksum = self._calc_checksum(usr_cfg)
                        tx = usr_cfg + ubinascii.unhexlify(hex(checksum)[-2:] + hex(checksum)[2:4])
                        self.uart.write(b"\x43\x43")
                        self.uart.write(tx)
                        utils.verbose("=> CC", constants.VERBOSE)
                        rx = self._get_reply()
                        if self._ack(rx):
                            utils.log_file("{} => uploaded deployment config".format(self.__qualname__))  # DEBUG
                            return True
                except:
                    break
        utils.log_file("{} => unable to upload deployment config".format(self.__qualname__))  # DEBUG
        return False

    def _set_start(self):
        """Computes the measurement starting time to be synced with scheduler."""
        now = utime.time() - self.config["Activation_Delay"]
        next = now - now % self.config["Activation_Rate"] + self.config["Activation_Rate"]
        if now % self.config["Activation_Rate"] > self.config["Activation_Rate"] - self.config["Samples"] // self.config["Sample_Rate"] - self.config["Adcp"]["Start_Delay"]:
          next += self.config["Activation_Rate"]
        next += - self.config["Samples"] // self.config["Sample_Rate"] // 2 - self.config["Adcp"]["Start_Delay"]
        next += self.config["Activation_Delay"]
        start = utime.localtime(next)
        start = ubinascii.unhexlify("{:02d}{:02d}{:02d}{:02d}{:02d}{:02d}".format(start[4], start[5], start[2], start[3], int(str(start[0])[2:]), start[1]))
        utils.log_file("{} => set start at {}".format(self.__qualname__, utils.time_string(next)))  # DEBUG
        return start

    def _get_usr_cfg(self):
        """Retreives the current deployment config from the instrument."""
        start = utime.time()
        while True:
            start = utime.time()
            while True:
                if self._timeout(start):
                    utils.log_file("{} => unable to retreive deployment config".format(self.__qualname__))  # DEBUG
                    return False
                if self._break():
                    utils.verbose("=> GC", constants.VERBOSE)
                    self.uart.write("GC")
                    rx = self._get_reply()
                    if self._ack(rx):
                        if self.verify_checksum(rx[:-2]):
                            self.usr_cfg = self._parse_usr_cfg(rx)
                            utils.log_file("{} => retreived deployment config".format(self.__qualname__))  # DEBUG
                            return True

    def _parse_usr_cfg(self, bytestring):
        """Parses the deployment constants."""
        return (
            "{:02x}".format(bytestring[0]),                                     # [0] Sync
            "{:02x}".format((int.from_bytes(bytestring[1:2], "little"))),       # [1] Id
            int.from_bytes(bytestring[2:4], "little"),                          # [2] Size
            int.from_bytes(bytestring[4:6], "little"),                          # [3] T1
            int.from_bytes(bytestring[6:8], "little"),                          # [4] T2, BlankingDistance
            int.from_bytes(bytestring[8:10], "little"),                         # [5] T3
            int.from_bytes(bytestring[10:12], "little"),                        # [6] T4
            int.from_bytes(bytestring[12:14], "little"),                        # [7] T5
            int.from_bytes(bytestring[14:16], "little"),                        # [8] NPings
            int.from_bytes(bytestring[16:18], "little"),                        # [9] AvgInterval
            int.from_bytes(bytestring[18:20], "little"),                        # [10] NBeams
            self._decode_usr_timctrlreg(int.from_bytes(bytestring[20:22], "little")),   # [11] TimCtrlReg
            self._decode_usr_pwrctrlreg(int.from_bytes(bytestring[22:24], "little")),   # [12] Pwrctrlreg
            bytestring[24:26],                                                  # [13] A1 Not used.
            bytestring[26:28],                                                  # [14] B0 Not used.
            bytestring[28:30],                                                  # [15] B1 Not used.
            int.from_bytes(bytestring[30:32], "little"),                        # [16] CompassUpdRate
            self.coord_system[int.from_bytes(bytestring[32:34], "little")],     # [17] CoordSystem
            int.from_bytes(bytestring[34:36], "little"),                        # [18] Nbins
            int.from_bytes(bytestring[36:38], "little"),                        # [19] BinLength
            int.from_bytes(bytestring[38:40], "little"),                        # [20] MeasInterval
            bytestring[40:46].decode("utf-8"),                                  # [21] DeployName
            int.from_bytes(bytestring[46:48], "little"),                        # [22] WrapMode
            ubinascii.hexlify(bytestring[48:54]).decode("utf-8"),               # [23] ClockDeploy
            int.from_bytes(bytestring[54:58], "little"),                        # [24] DiagInterval
            self._decode_usr_mode(int.from_bytes(bytestring[58:60], "little")), # [25] Mode
            int.from_bytes(bytestring[60:62], "little"),                        # [26] AdjSoundSpeed
            int.from_bytes(bytestring[62:64], "little"),                        # [27] NSampDiag
            int.from_bytes(bytestring[64:66], "little"),                        # [28] NbeamsCellDiag
            int.from_bytes(bytestring[66:68], "little"),                        # [29] NpingDiag
            self._decode_usr_modetest(int.from_bytes(bytestring[68:70], "little")),     # [30] ModeTest
            int.from_bytes(bytestring[68:72], "little"),                        # [31] AnaInAddr
            int.from_bytes(bytestring[72:74], "little"),                        # [32] SWVersion
            int.from_bytes(bytestring[74:76], "little"),                        # [33] Salinity
            ubinascii.hexlify(bytestring[76:256]),                              # [34] VelAdjTable
            bytestring[256:336].decode("utf-8"),                                # [35] Comments
            ubinascii.hexlify(bytestring[336:384]),                             # [36] Spare
            int.from_bytes(bytestring[384:386], "little"),                      # [37] Processing Method
            ubinascii.hexlify(bytestring[386:436]),                             # [38] Spare
            self._decode_usr_wavemode(int.from_bytes(bytestring[436:438], "little")),   # [39] Wave Measurement Mode
            int.from_bytes(bytestring[438:440], "little"),                      # [40] DynPercPos
            int.from_bytes(bytestring[440:442], "little"),                      # [41] T1
            int.from_bytes(bytestring[442:444], "little"),                      # [42] T2
            int.from_bytes(bytestring[444:446], "little"),                      # [43] T3
            int.from_bytes(bytestring[446:448], "little"),                      # [44] NSamp
            bytestring[448:450].decode("utf-8"),                                # [45] A1 Not used.
            bytestring[450:452].decode("utf-8"),                                # [46] B0 Not used.
            bytestring[452:454].decode("utf-8"),                                # [47] B1 Not used.
            ubinascii.hexlify(bytestring[454:456]),                             # [48] Spare
            int.from_bytes(bytestring[456:458], "little"),                      # [49] AnaOutScale
            int.from_bytes(bytestring[458:460], "little"),                      # [50] CorrThresh
            ubinascii.hexlify(bytestring[460:462]),                             # [51] Spare
            int.from_bytes(bytestring[462:464], "little"),                      # [52] TiLag2
            ubinascii.hexlify(bytestring[464:486]),                             # [53] Spare
            bytestring[486:510]                                                 # [54] QualConst
            )

    def _decode_usr_timctrlreg(self, bytestring):
        """Decodes timing control register."""
        timctrlreg = "{:016b}".format(bytestring)
        return timctrlreg

    def _decode_usr_pwrctrlreg(self, bytestring):
        """Decodes power control register."""
        pwrctrlreg = "{:016b}".format(bytestring)
        return pwrctrlreg

    def _decode_usr_mode(self, bytestring):
        """Decodes power control register."""
        mode = "{:016b}".format(bytestring)
        return mode

    def _decode_usr_modetest(self, bytestring):
        """Decodes power control register."""
        modetest = "{:016b}".format(bytestring)
        return modetest

    def _decode_usr_wavemode(self, bytestring):
        """Decodes power control register."""
        wavemode = "{:016b}".format(bytestring)
        return wavemode

    def _get_head_cfg(self):
        """Retreives the current head config from the instrument."""
        start = utime.time()
        while True:
            if self._timeout(start):
                utils.log_file("{} => unable to retreive head config".format(self.__qualname__))  # DEBUG
                return False
            if self._break():
                utils.verbose("=> GH", constants.VERBOSE)
                self.uart.write("GH")
                rx = self._get_reply()
                if self._ack(rx):
                    if self.verify_checksum(rx[:-2]):
                        self.head_cfg = self._parse_head_cfg(rx)
                        utils.log_file("{} => retreived head config".format(self.__qualname__))  # DEBUG
                        return True

    def _parse_head_cfg(self, bytestring):
        """Parses the head constants."""
        return (
            "{:02x}".format(bytestring[0]),                                     # [0] Sync
            "{:02x}".format(int.from_bytes(bytestring[1:2], "little")),         # [1] Id
            int.from_bytes(bytestring[2:4], "little") * 2,                      # [2] Size
            self._decode_head_cfg(int.from_bytes(bytestring[4:6], "little")),   # [3] Config
            int.from_bytes(bytestring[6:8], "little"),                          # [4] Frequency
            bytestring[8:10],                                                   # [5] Type
            bytestring[10:22].decode("ascii"),                                  # [6] SerialNo
            bytestring[22:198],                                                 # [7] System
            bytestring[198:220],                                                # [8] Spare
            int.from_bytes(bytestring[220:222], "little")                       # [9] NBeams
            )

    def _decode_head_cfg(self, cfg):
        """Decodes the head constants."""
        return (
            "PRESSURE SENSOR {}".format("YES" if cfg >> 0 & 1  else "NO"),
            "MAGNETOMETER SENSOR {}".format("YES" if cfg >> 1 & 1  else "NO"),
            "PRESSURE SENSOR {}".format("YES" if cfg >> 2 & 1  else "NO"),
            "{}".format("DOWN" if cfg >> 3 & 1  else "UP")
            )

    def _get_status(self, status):
        """Decodes the tilt mounting."""
        return(
            "{}".format("DOWN" if status >> 0 & 1 else "UP"),
            "SCALING {} mm/s".format("0.1" if status >> 1 & 1 else "1"),
            "PITCH {}".format("OUT OF RANGE" if status >> 2 & 2 else "OK"),
            "ROLL {}".format("OUT OF RANGE" if status >> 3 & 1 else "OK"),
            self._get_wkup_state(status),
            self._get_power_level(status)
            )

    def _get_wkup_state(self, status):
        """Decodes the wakeup state."""
        return (
            "WKUP STATE {}".format(
                "BAD POWER" if ~ status >> 5 & 1 and ~ status >> 4 & 1 else
                "POWER APPLIED" if ~ status >> 5 & 1 and status >> 4 & 1 else
                "BREAK" if status >> 5 & 1 and ~ status >> 4 & 1 else
                "RTC ALARM" if status >> 5 & 1 and status >> 4 & 1 else None)
            )

    def _get_power_level(self, status):
        """Decodes the power level."""
        return (
            "POWER LEVEL {}".format(
                "0" if ~ status >> 7 & 1 and ~ status >> 6 & 1 else
                "1" if ~ status >> 7 & 1 and status >> 6 & 1 else
                "2" if status >> 7 & 1 and ~ status >> 6 & 1 else
                "3" if status >> 7 & 1 and status >> 6 & 1 else None)
            )

    def _get_error(self, error):
        """Decodes the error codes."""
        return(
            "COMPASS {}".format("ERROR" if error >> 0 & 1 else "OK"),
            "MEASUREMENT DATA {}".format("ERROR" if error >> 1 & 1 else "OK"),
            "SENSOR DATA {}".format("ERROR" if error >> 2 & 2 else "OK"),
            "TAG BIT {}".format("ERROR" if error >> 3 & 1 else "OK"),
            "FLASH {}".format("ERROR" if error >> 4 & 1 else "OK"),
            "BEAM NUMBER {}".format("ERROR" if error >> 5 & 1 else "OK"),
            "COORD. TRANSF. {}".format("ERROR" if error >> 3 & 1 else "OK")
            )

    def _dump_recorder(self):
        pass  # TODO

    def _format_recorder(self):
        """Erase all recorded data if it reached the maximum allowed files number (31)"""
        start = utime.time()
        while True:
            if self._timeout(start):
                utils.log_file("{} => unable to format recorder".format(self.__qualname__))  # DEBUG
                return False
            if self._break():
                utils.verbose("=> FO", constants.VERBOSE)
                self.uart.write(b"\x46\x4F\x12\xD4\x1E\xEF")
                if self._ack(self._get_reply()):
                    utils.log_file("{} => recorder formatted".format(self.__qualname__))  # DEBUG
                    return True

    def _acquire_data(self):
        """Starts a single measurement based on the current configuration of the
        instrument without storing data to the recorder. Instrument enters Power
        Down Mode when measurement has been made.
        """
        utils.log_file("{} => acquiring 1 sample...".format(self.__qualname__))  # DEBUG
        start = utime.time()
        while True:
            if self._timeout(start):
                return False
            if self._break():
                utils.verbose("=> AD", constants.VERBOSE)
                self.uart.write("AD")
                if self._ack(self._get_reply()):
                    rx = self._get_reply()
                    if self.verify_checksum(rx):
                        return rx

    def _start_delayed(self):
        """Starts a measurement at a specified time based on the current
        configuration of the instrument. Data is stored to a new file in
        the recorder. Data is output on the serial port only if specified in
        the configuration.
        """
        start = utime.time()
        while True:
            if self._timeout(start):
                utils.log_file("{} => unable to start measurement".format(self.__qualname__))  # DEBUG
                return False
            if self._break():
                utils.verbose("=> SD", constants.VERBOSE)
                self.uart.write("SD")
                rx = self._get_reply()
                if not self._ack(rx):
                    self._format_recorder()
                else:
                    utils.log_file("{} => measurement started".format(self.__qualname__))  # DEBUG
                    return True

    def _conv_data(self, bytestring):
        """Converts sample bytestring to ascii string."""
        return (
            ubinascii.hexlify(bytestring[9:10]),                                # [0] Month
            ubinascii.hexlify(bytestring[6:7]),                                 # [1] Day
            ubinascii.hexlify(bytestring[8:9]),                                 # [2] Year
            ubinascii.hexlify(bytestring[7:8]),                                 # [3] Hour
            ubinascii.hexlify(bytestring[4:5]),                                 # [4] Minute
            ubinascii.hexlify(bytestring[5:6]),                                 # [5] Second
            self._get_error(int.from_bytes(bytestring[10:12], "little")),       # [6] Error code
            self._get_status(int.from_bytes(bytestring[25:26], "little")),      # [7] Status code
            int.from_bytes(bytestring[14:16], "little") / 10,                   # [8] Battery voltage
            int.from_bytes(bytestring[16:18], "little") / 10,                   # [9] Soundspeed
            int.from_bytes(bytestring[18:20], "little") / 10,                   # [10] Heading
            int.from_bytes(bytestring[20:22], "little") / 10,                   # [11] Pitch
            int.from_bytes(bytestring[22:24], "little") / 10,                   # [12] Roll
            self._calc_pressure(bytestring[24:25], bytestring[26:28]) / 1000,   # [13] Pressure
            int.from_bytes(bytestring[28:30], "little") / 100,                  # [14] Temperature
            int.from_bytes(bytestring[12:14], "little") / 10,                   # [15] Analog input 1
            int.from_bytes(bytestring[16:18], "little") / 10                    # [16] Analog input 2
            ) + self._get_cells(bytestring[30:])                                # [17:] x1,y1,z1, x2, y2, z2, x3, y3, z3...

    def _calc_pressure(self, pressureMSB, pressureLSW):
        """Calculates pressure value.

        Params:
            pressureMSB, pressureLSW(float)
        Returns:
            pressure(float)
        """
        return 65536 * int.from_bytes(pressureMSB, "little") + int.from_bytes(pressureLSW, "little")

    def _get_cells(self, bytestring):
        """Extracts cells data from sample bytestring.

        Params:
            bytestring
        Returns:
            list(x1, x2, x3... y1, y2, y3... z1, z2, z3..., a11, a12 , a13..., a21, a22, a23..., a31, a32, a33...)
        """
        cells = []
        if self.usr_cfg:
            nbins = self.usr_cfg[18]
            nbeams = self.usr_cfg[10]
            j = 0
            for beam in range(nbeams):
                for bin in range(nbins):
                    cells.append(int.from_bytes(bytestring[j:j+2], "little"))
                    j += 2
            for beam in range(nbeams):
                for bin in range(nbins):
                    cells.append(int.from_bytes(bytestring[j:j+1], "little"))
                    j += 1
        return tuple(cells)

    def _format_data(self, sample):
        """Formats data according to output format."""
        data = [
            "{:2s}/{:2s}/20{:2s}".format(sample[1], sample[0], sample[2]),  # dd/mm/yyyy
            "{:2s}:{:2s}".format(sample[3], sample[4]),                     # hh:mm
            "{}".format(sample[8]),                                         # Battery
            "{}".format(sample[9]),                                         # SoundSpeed
            "{}".format(sample[10]),                                        # Heading
            "{}".format(sample[11]),                                        # Pitch
            "{}".format(sample[12]),                                        # Roll
            "{}".format(sample[13]),                                        # Pressure
            "{}".format(sample[14]),                                        # Temperature
            "{}".format(self._get_flow()),                                  # Flow
            "{}".format(self.usr_cfg[17]),                                  # CoordSystem
            "{}".format(self.usr_cfg[4]),                                   # BlankingDistance
            "{}".format(self.usr_cfg[20]),                                  # MeasInterval
            "{}".format(self.usr_cfg[19]),                                  # BinLength
            "{}".format(self.usr_cfg[18]),                                  # NBins
            "{}".format(self.head_cfg[3][3]),                               # TiltSensorMounting
            ]
        j = 17
        for bin in range(self.usr_cfg[18]):
            data.append("#{}".format(bin + 1))                              # (#Cell number)
            for beam in range(self.usr_cfg[10]):
                data.append("{}".format(sample[j]))                         # East, North, Up/Down
                j += 1
        return data

    def _get_flow(self):
        """Calculates the fluid flow (rivers only)."""
        # TODO
        pass

    """def _rel_sample(self, sample):
        velocity = []
        direction = []
        nbins = self.usr_cfg[18]
        nbeams = self.usr_cfg[10]
        if sample:
            sample = sample[17:]
            i = 0
            for bin in range(nbins):
                velocity.append(math.sqrt(math.pow(sample[i],2)+math.pow(sample[i+nbins],2)))
                dir = math.degrees(math.acos(sample[i+nbins]/math.sqrt(math.pow(sample[i],2)+math.pow(sample[i+nbins],2))))
                if sample[i] < 0:
                    dir = 360 - dir
                direction.append(dir)
                i += 1
        return velocity, direction"""

    def _(self, bytestring):
        """Response to break commmand."""
        return bytestring.decode("utf-8")

    def _get_clock(self):
        """Reads the instrument RTC."""
        start = utime.time()
        while True:
            if self._timeout(start):
                return False
            if self._break():
                utils.verbose("=> RC", constants.VERBOSE)
                self.uart.write("RC")
                rx = self._get_reply()
                if self._ack(rx):
                    rx = ubinascii.hexlify(rx)
                    return "20{:2s}-{:2s}-{:2s} {:2s}:{:2s}:{:2s}".format(
                        rx[8:10], # Year
                        rx[10:12],# Month
                        rx[4:6],  # Day
                        rx[6:8],  # Hour
                        rx[0:2],  # Minute
                        rx[2:4])  # Seconds

    def _set_clock(self):
        """Sets up the instrument RTC.

        mm ss DD hh YY MM (3 words of 2 bytes each)
        """
        start = utime.time()
        while True:
            if self._timeout(start):
                utils.log_file("{} => unable to sync clock".format(self.__qualname__))  # DEBUG
                return False
            if self._break():
                now = utime.localtime()
                tx = "{:02d}{:02d}{:02d}{:02d}{:02d}{:02d}".format(now[4], now[5], now[2], now[3], int(str(now[0])[2:]), now[1])
                self.uart.write("SC")
                self.uart.write(ubinascii.unhexlify(tx))
                utils.verbose("=> SC" + str(tx), constants.VERBOSE)
                if self._ack(self._get_reply()):
                    utils.log_file("{} => clock synced (dev: {} board: {})".format(self.__qualname__, self._get_clock(), utils.time_string(utime.mktime(now))))  # DEBUG
                    return True

    def main(self):
        """Captures instrument data."""
        if not self.init_uart():
            return
        utils.log_file("{} => acquiring data...".format(self.__qualname__))  # DEBUG
        self.led_on()
        data = "$ADCP"
        start = utime.time()
        while True:
            if utime.time() - start > self.config["Samples"] // self.config["Sample_Rate"]:
                utils.log_file("{} => timeout occourred".format(self.__qualname__))  # DEBUG
                break
            if self.uart.any():
                data = ";".join([self.config["String_Label"]] + self._format_data(self._conv_data(self.uart.read())))
                break
        utils.log_data(data)
        self.led_on()
        return
