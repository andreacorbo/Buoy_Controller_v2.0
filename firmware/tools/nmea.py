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

import tools.utils as utils
import constants

class NMEA(object):

    def __init__(self, *args, **kwargs):
        self.new_sentence_flag = False
        self.checksum_flag = False
        self.checksum = ""
        self.word = ""
        self.sentence = []

    def verify_checksum(self, checksum, sentence):
        """Verifies the NMEA sentence integrity.

        Params:
            checksum(hex)
            sentence(list)
        """
        calculated_checksum = 0
        for char in ",".join(map(str, sentence)):
            calculated_checksum ^= ord(char)
        if "{:02X}".format(calculated_checksum) != checksum:
            utils.log_file("NMEA invalid checksum calculated: {:02X} got: {}".format(calculated_checksum, checksum), constants.LOG_LEVEL)
            return False
        else:
            return True

    def get_sentence(self, char_code, sentence):
        """Gets a single NMEA sentence, each sentence is a list of words itself.

        Params:
            char_code(int)
        """
        if char_code in range(32, 126):
            ascii_char = chr(char_code)
            if ascii_char == "$":
                self.new_sentence_flag = True
                self.word = ""
                self.sentence = []
                self.checksum = ""
                self.checksum_flag = False
            elif ascii_char == ",":
                if self.new_sentence_flag:
                    self.sentence.append(self.word)
                    self.word = ""
            elif ascii_char == "*":
                if self.new_sentence_flag:
                    self.sentence.append(self.word)
                    self.checksum_flag = True
            elif self.new_sentence_flag:
                if self.checksum_flag:
                    self.checksum = self.checksum + ascii_char
                    if len(self.checksum) == 2:
                        if self.verify_checksum(self.checksum, self.sentence):
                            if sentence and self.sentence[0][-3:] == sentence:
                                return True
                else:
                    self.word = self.word + ascii_char

    def is_valid_gprmc(self):
        """Checks if a GPRMC sentence contains valid data.

        Returns:
          True or False
        """
        if self.sentence[2] == "A":
            return True
        return False
