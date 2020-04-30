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
import uos
import sys
from tools.functools import partial
import tools.utils as utils

#
# Protocol bytes
#
SOH = b"\x01"  # 1
STX = b"\x02"  # 2
EOT = b"\x04"  # 4
ACK = b"\x06"  # 6
NAK = b"\x15"  # 21
CAN = b"\x18"  # 24
C = b"\x43"  # 67


class YMODEM(object):
    #
    # crctab calculated by Mark G. Mendel, Network Systems Corporation
    #
    crctable = [
        0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
        0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
        0x1231, 0x0210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7, 0x62d6,
        0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
        0x2462, 0x3443, 0x0420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485,
        0xa56a, 0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d,
        0x3653, 0x2672, 0x1611, 0x0630, 0x76d7, 0x66f6, 0x5695, 0x46b4,
        0xb75b, 0xa77a, 0x9719, 0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc,
        0x48c4, 0x58e5, 0x6886, 0x78a7, 0x0840, 0x1861, 0x2802, 0x3823,
        0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948, 0x9969, 0xa90a, 0xb92b,
        0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0x0a50, 0x3a33, 0x2a12,
        0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b, 0xab1a,
        0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0x0c60, 0x1c41,
        0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49,
        0x7e97, 0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0x0e70,
        0xff9f, 0xefbe, 0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78,
        0x9188, 0x81a9, 0xb1ca, 0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f,
        0x1080, 0x00a1, 0x30c2, 0x20e3, 0x5004, 0x4025, 0x7046, 0x6067,
        0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d, 0xd31c, 0xe37f, 0xf35e,
        0x02b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214, 0x6277, 0x7256,
        0xb5ea, 0xa5cb, 0x95a8, 0x8589, 0xf56e, 0xe54f, 0xd52c, 0xc50d,
        0x34e2, 0x24c3, 0x14a0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
        0xa7db, 0xb7fa, 0x8799, 0x97b8, 0xe75f, 0xf77e, 0xc71d, 0xd73c,
        0x26d3, 0x36f2, 0x0691, 0x16b0, 0x6657, 0x7676, 0x4615, 0x5634,
        0xd94c, 0xc96d, 0xf90e, 0xe92f, 0x99c8, 0x89e9, 0xb98a, 0xa9ab,
        0x5844, 0x4865, 0x7806, 0x6827, 0x18c0, 0x08e1, 0x3882, 0x28a3,
        0xcb7d, 0xdb5c, 0xeb3f, 0xfb1e, 0x8bf9, 0x9bd8, 0xabbb, 0xbb9a,
        0x4a75, 0x5a54, 0x6a37, 0x7a16, 0x0af1, 0x1ad0, 0x2ab3, 0x3a92,
        0xfd2e, 0xed0f, 0xdd6c, 0xcd4d, 0xbdaa, 0xad8b, 0x9de8, 0x8dc9,
        0x7c26, 0x6c07, 0x5c64, 0x4c45, 0x3ca2, 0x2c83, 0x1ce0, 0x0cc1,
        0xef1f, 0xff3e, 0xcf5d, 0xdf7c, 0xaf9b, 0xbfba, 0x8fd9, 0x9ff8,
        0x6e17, 0x7e36, 0x4e55, 0x5e74, 0x2e93, 0x3eb2, 0x0ed1, 0x1ef0,
    ]


    def __init__(self, _getc, _putc, mode="Ymodem", pad=b"\x1a"):
        self._getc = _getc
        self._putc = _putc
        self.mode = mode
        self.pad = pad
        self.break_condition = len(utils.processes)

    def _time_to_stop(self):
        """Aborts transmission if and external stop flag is set."""
        if self.break_condition > 1:
            self.abort()

    def abort(self, count=2, timeout=60):
        """Sends an abort sequence using CAN byte.

        Params:
            count(int)
            timeout(int): seconds
        """
        for _ in range(count):
            self._putc(CAN, timeout)  # handle tx errors
            print("CANCEL TRANSMISSION...")

    def _ack(self, error_count, retry):
        while True:
            if error_count == retry:
                print("TOO MANY ERRORS, ABORTING...")
                return False  # Exit
            if not self._putc(ACK):  # handle tx errors
                print("ERROR SENDING ACK, RETRY...")
                error_count += 1
                continue
            print("ACK -->")
            break
        return True


    def _clear(self, error_count, retry):
        while True:
            if error_count == retry:
                print("TOO MANY ERRORS, ABORTING...")
                return False  # Exit
            if not self._putc(C):  # handle tx errors
                print("ERROR SENDING C, RETRY...")
                error_count += 1
                continue
            print("C -->")
            break
        return True


    def _nak(self, error_count, retry):
        while True:
            if error_count == retry:
                print("TOO MANY ERRORS, ABORTING...")
                return False  # Exit
            if not self._putc(NAK):  # handle tx errors
                print("ERROR SENDING NAK, RETRY...")
                error_count += 1
                continue
            print("NAK -->")
            break
        return True


    def _verify_recvd_checksum(self, crc_mode, data):
        #
        # Verifiy the received CRC or checksum
        #
        if crc_mode:
            _checksum = bytearray(data[-2:])
            received_sum = (_checksum[0] << 8) + _checksum[1]
            data = data[:-2]
            calculated_sum = self._calc_crc(data)
            valid = bool(received_sum == calculated_sum)
            if not valid:
                print("CHECKSUM FAIL EXPECTED({:04x}) GOT({:4x})".format(received_sum, calculated_sum))
        else:
            _checksum = bytearray([data[-1]])
            received_sum = _checksum[0]
            data = data[:-1]

            calculated_sum = self._calc_checksum(data)
            valid = received_sum == calculated_sum
            if not valid:
                print("CHECKSUM FAIL EXPECTED({:02x}) GOT({:2x})".format(received_sum, calculated_sum))
        return valid, data

    def _set_last_byte(self, tmp_file, pointer):
        """Stores sent bytes counter into temp file.

        Params:
            tmp_file(str)
            pointer(int)
        """
        with open(tmp_file, "w") as part:
            part.write(str(pointer))


    def _get_last_byte(self, tmp_file, stream):
        """Gets sent bytes number from temp file.

        Params:
            tmp_file(str)
            stream(bytes)
        """
        pointer = 0
        try:
            with open(tmp_file, "r") as part:
                pointer = int(part.read())
        except:
            pass
        stream.seek(pointer)


    def _is_new_day(self, file):
        """Checks if file is older than one day.

        Params:
            file(str)

        Returns:
            True or False
        """
        now = utime.time() - utime.time() % 86400
        try:
            last_file_write = uos.stat(file)[8] - uos.stat(file)[8] % 86400
            if now - last_file_write >= 86400:
                return True
            return False
        except:
            return False


    def _totally_sent(self, file, tmp_file, sent_file):
        """Marks file as sent.

        Params:
            tmp_file(str)
            sent_file(str)
        """
        if self._is_new_day(file):
            try:
                uos.rename(file, sent_file)
                try:
                    uos.remove(tmp_file)
                except:
                    print("UNABLE TO REMOVE {} FILE".format(tmp_file))
            except:
                print("UNABLE TO RENAME {} FILE".format(file))


    def _make_filename_header(self, packet_size):
        """Builds filename packet header.

        Params:
            packet_size(int)
        """
        _bytes = []
        if packet_size == 128:
            _bytes.append(ord(SOH))
        elif packet_size == 1024:
            _bytes.append(ord(STX))
        _bytes.extend([0x00, 0xff])
        return bytearray(_bytes)


    def _make_data_header(self, packet_size, sequence):
        """Builds data packet header.

        Params:
            packet_size(int)
            sequence(int)
        """
        assert packet_size in (128, 1024), packet_size
        _bytes = []
        if packet_size == 128:
            _bytes.append(ord(SOH))
        elif packet_size == 1024:
            _bytes.append(ord(STX))
        _bytes.extend([sequence, 0xff - sequence])
        return bytearray(_bytes)


    def _make_checksum(self, crc_mode, data):
        """Creates data checksum.

        Params:
            crc_mode(int)
            data(str)
        """
        _bytes = []
        if crc_mode:
            crc = self._calc_crc(data)
            _bytes.extend([crc >> 8, crc & 0xff])
        else:
            crc = self._calc_checksum(data)
            _bytes.append(crc)
        return bytearray(_bytes)


    def _calc_checksum(self, data, checksum=0):
        """Calculates the checksum for a given block of data.

        Params:
            data(str)
            checksum(int): default[0]
        Returns:
            checksum(hex)
        """
        return (sum(map(ord, data)) + checksum) % 256


    def _calc_crc(self, data, crc=0):
        """Calculates the 16 bit Cyclic Redundancy Check for a given block of data

        Params:
            data(str)
            crc(int): default[0]
        Returns:
            crc(hex)
        """
        for char in bytearray(data):
            crctbl_idx = ((crc >> 8) ^ char) & 0xff
            crc = ((crc << 8) ^ self.crctable[crctbl_idx]) & 0xffff
        return crc & 0xffff


    def send(self, files, tmp_file_pfx, sent_file_pfx, retry=5, timeout=10):
        """Sends files according to ymodem protocol.

        Params:
            files(list)
            tmp_file_pfx(str)
            sent_file_pfx(str)
            retry(int): default[5]
            timeout(int): seconds, default[10]
        """
        #
        # Initialize transaction
        #
        try:
            packet_size = dict(Ymodem = 128, Ymodem1k = 1024)[self.mode]
        except KeyError:
            raise ValueError("INVALID MODE {self.mode}".format(self=self))
        error_count = 0
        crc_mode = 0
        cancel = 0
        print("BEGIN TRANSACTION, PACKET SIZE {}".format(packet_size))
        #
        # Set 16 bit CRC or standard checksum mode
        #
        while True:
            char = self._getc(1, timeout)
            if error_count == retry:
                print("TOO MANY ERRORS, ABORTING...")
                return False  # Exit
            elif not char:
                print("TIMEOUT OCCURRED, RETRY...")
                error_count += 1
            elif char == C:
                print("<-- C")
                print("16 BIT CRC REQUESTED")
                crc_mode = 1
                error_count = 0
                break
            elif char == NAK:
                print("<-- NAK")
                print("STANDARD CECKSUM REQUESTED")
                crc_mode = 0
                error_count = 0
                break
            else:
                print("UNATTENDED CHAR {}, RETRY...".format(char))
                error_count += 1
        #
        # Iterate over file list
        #
        files.extend("\x00")  # add a null file to list to handle eot
        file_count = 0
        for file in files:
            #
            # Set stream pointer (read file from last tansmitted byte)
            #
            tmp_file = file.replace(file.split("/")[-1], tmp_file_pfx + file.split("/")[-1])
            sent_file = file.replace(file.split("/")[-1], sent_file_pfx + file.split("/")[-1])
            filename = file.split("/")[-1]
            if file != "\x00":
                try:
                    stream = open(file)
                except:
                    print("UNABLE TO OPEN {}, TRY NEXT FILE...".format(file))
                    continue
                self._get_last_byte(tmp_file, stream)  # read last byte from $file
                pointer = stream.tell()  # set stream pointer
                if pointer == uos.stat(file)[6]:  # check if pointer correspond to file size
                    print("FILE {} ALREADY TRANSMITTED, SEND NEXT FILE...".format(filename))
                    stream.close()
                    self._totally_sent(file, tmp_file, sent_file)
                    continue  # open next file
            file_count += 1
            #
            # Wait for _clear to send (if there are more than one file)
            #
            if file_count > 1:
                while True:
                    char = self._getc(1, timeout)
                    if error_count == retry:
                        print("TOO MANY ERRORS, ABORTING...")
                        return False  # Exit
                    if not char:  # handle rx errors
                        print("TIMEOUT OCCURRED, RETRY...")
                        error_count += 1
                    elif char == C:
                        print("<-- C")
                        error_count = 0
                        break
                    else:
                        print("UNATTENDED CHAR {}, RETRY...".format(char))
                        error_count += 1
            #
            # Create file name packet
            #
            header = self._make_filename_header(packet_size)  # create file packet
            data = bytearray(filename + "\x00")  # filename + space
            if file != "\x00":
                data.extend(str(uos.stat(file)[6] - pointer))  # Sends data size to be transmitted
            padding = bytearray(packet_size - len(data))  # fill packet size with null char
            data.extend(padding)
            checksum = self._make_checksum(crc_mode, data)  # create packet checksum
            ackd  = 0
            while True and not self._time_to_stop():
                #
                # Send packet
                #
                while True and not self._time_to_stop():
                    if error_count == retry:
                        print("TOO MANY ERRORS, ABORTING...")
                        return False  # Exit
                    if not self._putc(header + data +checksum):  # handle tx errors
                        error_count += 1
                        continue
                    print("SENDING FILE {}".format(filename))
                    break
                #
                # Wait for reply
                #
                while True:
                    char = self._getc(1, timeout)
                    if error_count == retry:
                        print("TOO MANY ERRORS, ABORTING...")
                        return False  # Exit
                    if not char:  # handle rx erros
                        print("TIMEOUT OCCURRED, RETRY...")
                        error_count += 1
                        break  # resend packet
                    elif char == ACK :
                        print("<-- ACK")
                        if data == bytearray(packet_size):
                            print("TRANSMISSION COMPLETE, EXITING...")
                            return True # Exit
                        else:
                            error_count = 0
                            ackd = 1
                            break
                    elif char == CAN:
                        print("<-- CAN")
                        if cancel:
                            print("TRANSMISSION CANCELED BY RECEIVER")
                            return False  # Exit
                        else:
                            cancel = 1
                            error_count = 0
                            continue  # wait for a second CAN
                    else:
                        print("UNATTENDED CHAR {}, RETRY...".format(char))
                        error_count += 1
                        break  # resend packet
                if ackd:
                    break  # wait for data
            #
            # Waiting for _clear to send
            #
            while True:
                char = self._getc(1, timeout)
                if error_count == retry:
                    print("TOO MANY ERRORS, ABORTING...")
                    return False # Exit
                if not char:  # handle rx errors
                    print("TIMEOUT OCCURRED, RETRY...")
                    error_count += 1
                elif char == C:
                    print("<-- C")
                    error_count = 0
                    break
                else:
                    print("UNATTENDED CHAR {}, RETRY...".format(char))
                    error_count += 1
            #
            # Send file
            #
            success_count = 0
            total_packets = 0
            sequence = 1
            cancel = 0
            while True and not self._time_to_stop():
                #
                # Create data packet
                #
                data = stream.read(packet_size)  # read a bytes packet

                if not data:  # file reached eof send eot
                    print("EOF")
                    break
                total_packets += 1

                header = self._make_data_header(packet_size, sequence)  # create header
                format_string = "{:"+self.pad.decode("utf-8")+"<"+str(packet_size)+"}"  # right fill data with pad byte
                data = format_string.format(data)  # create packet data
                checksum = self._make_checksum(crc_mode, data)  # create checksum
                ackd = 0
                while True and not self._time_to_stop():
                    #
                    # Send data packet
                    #
                    while True  and not self._time_to_stop():
                        if error_count == retry:
                            print("TOO MANY ERRORS, ABORTING...")
                            return False  # Exit
                        if not self._putc(header + data + checksum):  # handle tx errors
                            error_count += 1
                            continue  # resend packet
                        print("PACKET {} -->".format(sequence))
                        break
                    #
                    # Wait for reply
                    #
                    while True:
                        char = self._getc(1, timeout)
                        if not char:  # handle rx errors
                            print("TIMEOUT OCCURRED, RETRY...")
                            error_count += 1
                            break  # resend packet
                        elif char == ACK:
                            print("<-- ACK")
                            ackd = 1
                            success_count += 1
                            error_count = 0
                            pointer = stream.tell()  # move pointer to next packet start byte
                            self._set_last_byte(tmp_file, pointer)  # keep track of last successfully transmitted packet
                            sequence = (sequence + 1) % 0x100  # keep track of sequence
                            break  # send next packet
                        elif char == NAK:
                            print("<-- NAK")
                            error_count += 1
                            break  # resend packet
                        elif char == CAN:
                            print("<-- CAN")
                            if cancel:
                                print("TRANSMISSION CANCELED BY RECEIVER")
                                return False  # Exit
                            else:
                                cancel = 1
                                error_count = 0
                        else:
                            print("UNATTENDED CHAR {}, RETRY...".format(char))
                            error_count += 1
                            break  # resend packet
                    if ackd:
                        break  # send next packet
            #
            # End of transmission
            #
            while True:
                if error_count == retry:
                    print("TOO MANY ERRORS, ABORTING...")
                    return False  # Exit
                if not self._putc(EOT):  # handle tx errors
                    error_count += 1
                    continue  # resend EOT
                print("EOT -->")
                char = self._getc(1, timeout)  # waiting for reply
                if not char:  # handle rx errors
                    print("TIMEOUT OCCURRED, RETRY...")
                    error_count += 1
                elif char == ACK:
                    print("<-- ACK")
                    print("FILE {} SUCCESSFULLY TRANSMITTED".format(filename))
                    self._totally_sent(file, tmp_file, sent_file)
                    stream.close()
                    error_count = 0
                    break  # send next file
                else:
                    print("UNATTENDED CHAR {}, RETRY...".format(char))
                    error_count += 1

    def recv(self, datapath="/", crc_mode=1, retry=5 , timeout=10):
        """Receives files according to ymodem protocol.

        Params:
            datapath(str)
            retry(int): default[5]
            timeout(int): seconds, default[10]
        """#
        # Initialize transaction
        #
        error_count = 0
        while True:
            if crc_mode:
                #
                # Send C to request 16 bit CRC as first choice
                #
                while True:
                    if error_count > (retry // 2):
                        print("TOO MANY ERRORS, USE STANDARD CHECKSUM...")
                        crc_mode = 0
                        error_count = 0
                        break
                    if not self._putc(C):  # handle tx errors
                        print("ERROR SENDING C, RETRY...")
                        error_count += 1
                        continue
                    print("C -->")
                    error_count = 0
                    break
            else:
                #
                # Send NAK to request standard checksum as fall back
                #
                if not self.nack(error_count, retry):
                    return False  # Exits
                error_count = 0
            break
        #
        # Receive packet
        #
        char = 0
        packet_size = 128
        cancel = 0
        sequence = 0
        income_size = 0
        while True:
            t = utime.time()
            while not self.uart.any():
                if utime.time() - t >= timeout:  # Exists if sender does not respond
                    return False
                pass
            char = self._getc(1,timeout)
            if error_count == retry:
                print("TOO MANY ERRORS, ABORTING...")
                self.abort(timeout=timeout)  # Cancels transmission
                return False  # Exits
            elif not char:  # handle rx errors
                print("TIMEOUT OCCURRED, RETRY...")
                error_count += 1
                continue
            elif char == CAN:
                print("<-- CAN")
                if cancel:
                    print("TRANSMISSION CANCELED BY SENDER")
                    return False  # Exits
                else:
                    cancel = 1
                    error_count = 0
            elif char == SOH:
                print("SOH <--")
                if packet_size != 128:
                    print("USING 128 BYTES PACKET SIZE")
                    packet_size = 128
                error_count = 0
            elif char == STX:
                print("STX <--")
                if packet_size != 1024:
                    print("USING 1 KB PACKET SIZE")
                    packet_size = 1024
                error_count = 0
            elif char == EOT:
                print("EOT <--")
                #
                # Acknowledge EOT
                #
                if not self._ack(error_count, retry):
                    return False  # Exits
                error_count = 0
                sequence = 0
                income_size = 0
                #
                # Clear to receive
                #
                if not self._clear(error_count, retry):
                    return False  # Exits
                error_count = 0
                continue
            else:
                print("UNATTENDED CHAR {}".format(char))
                error_count += 1
                continue
            #
            # Read sequence
            #
            while True:
                seq1 = self._getc(1, timeout)
                if not seq1:
                    print("FAILED TO GET FIRST SEQUENCE BYTE")
                    seq2 = None
                else:
                    seq1 = ord(seq1)
                    seq2 = self._getc(1, timeout)
                    if not seq2:
                        print("FAILED TO GET SECOND SEQUENCE BYTE")
                    else:
                        seq2 = 0xff - ord(seq2)
                        print("PACKET {} <--".format(sequence))
                if not (seq1 == seq2 == sequence):
                    print("SEQUENCE ERROR, EXPECTED {} GOT {}, DISCARD DATA".format(sequence, seq1))
                    self._getc(packet_size + 1 + crc_mode)  # Discard data packet
                    #
                    # Resend missed acknowledge
                    #
                    if not self._ack(error_count, retry):
                        return False  # Exits
                    error_count += 1
                    #
                    # If receiving file name packet, _clear for transmission
                    #
                    if seq1 == 0:
                        #
                        # Clear to receive
                        #
                        if not self._clear(error_count, retry):
                            return False  # Exits
                        error_count = 0
                else:
                    data = self._getc(packet_size + 1 + crc_mode, timeout)
                    print(data)
                    valid, data = self._verify_recvd_checksum(crc_mode, data)
                    if not valid:
                        #
                        # Not aknowledge packet, request retransmission
                        #
                        if not self._nak(error_count, retry):
                            return False  # Exits
                        error_count = 0
                    else:
                        if sequence == 0:  # Sequence 0 contains file name
                            if data[0:1] == b"\x00":  # Sequence 0 with null pathname state end of trasmission
                                #
                                # Acknowledge EOT
                                #
                                if not self._ack(error_count, retry):
                                    return False  # Exits
                                print("END OF TRANSMISSION")
                                return True  # Exits end of transmission
                            data_string = []
                            data_field = ""
                            for byte_ in data:
                                if byte_ != 0:
                                    data_field += chr(byte_)
                                elif len(data_field) > 0:
                                    data_string.append(data_field)
                                    data_field = ""
                            pathname = data_string[0]
                            attributes = data_string[1].split(" ")  # Length, modification date, mode, serial number...
                            length = int(attributes[0])
                            mod_date = int(attributes[1])
                            stream = open(pathname, "ab")
                            if stream:
                                print("RECEIVING FILE {}".format(pathname))
                                #
                                # Acknowledge packet
                                #
                                if not self._ack(error_count, retry):
                                    return False  # Exits
                                error_count = 0
                                #
                                # Clear for transmission
                                #
                                if not self._clear(error_count, retry):
                                    return False  # Exits
                                error_count = 0
                            else:
                                self.abort(timeout=timeout)  # Cancel transmission if file cannot be opened
                                return False  # Exits
                        else:
                            income_size += len(data)
                            trailing_null = income_size - length  # null trailing char
                            stream.write(data[:-trailing_null])  # exclude null trailing chars
                            #
                            # Acknowledge packet
                            #
                            if not self._ack(error_count, retry):
                                return False  # Exits
                            error_count = 0
                        sequence = (sequence + 1) % 0x100
                break

YMODEM1k = partial(YMODEM, mode="Ymodem1k")
