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
import tools.utils as utils
import constants
import _thread

class SCHEDULER(object):

    def __init__(self):
        utils.log_file("Initializing the event table...", constants.LOG_LEVEL)
        self.calc_event_table()

    def scheduled(self, timestamp):
        """Executes any event defined at occurred timestamp.

        Params:
            timestamp(int)
        """
        self.calc_next_event()
        if timestamp > self.next_event:  # Executes missed event.
            timestamp = self.next_event
        if timestamp in self.event_table:
            for device in self.event_table[timestamp]:
                self.manage_task(device, self.event_table[timestamp][device])
            self.calc_event_table()
            self.calc_next_event()

    def calc_next_event(self):
        """Gets the earlier event from the event table."""
        self.next_event = min(self.event_table)

    def manage_task(self, device, tasks):
        """Manages the device status after a event event.

        |--OFF--> ON--> WARMING UP--> READY-->|--OFF--|->

        Params:
            task(str)
        """
        if "on" in tasks:
            utils.create_device(device, tasks=["on"])
        elif "off" in tasks:
            utils.create_device(device, tasks=["off"])
        else:
            utils.status_table[device] = 2  # Sets device ready.
            _thread.start_new_thread(utils.execute, (device, tasks,))
            utils.log_file("{} => {}".format(device, constants.DEVICE_STATUS[utils.status_table[device]]), constants.LOG_LEVEL)

    def calc_data_acquisition_interval(self, device):
        tmp = [constants.DATA_ACQUISITION_INTERVAL]
        if device.split(".")[1] in constants.SCHEDULER:
            for event in constants.SCHEDULER[device.split(".")[1]]:
                if event == "log":
                    tmp = constants.SCHEDULER[device.split(".")[1]]["log"]
                else:
                    tmp.append(constants.SCHEDULER[device.split(".")[1]][event])
        return min(tmp)

    def calc_event_table(self):
        """Calculates the subsequent event for all defined devices."""
        self.event_table = {} # {timestamp:{device1:[task1, task2,...],...}
        now = utime.time()
        for device in utils.status_table:
            status = utils.status_table[device]
            data_aquisition_interval = self.calc_data_acquisition_interval(device)
            next_acquisition = now - now % data_aquisition_interval + data_aquisition_interval
            obj = utils.create_device(device)
            activation_delay = obj.config["Activation_Delay"]
            warmup_duration = obj.config["Warmup_Duration"]
            samples = obj.config["Samples"]
            sample_rate = obj.config["Sample_Rate"]
            try:
                sampling_duration = samples // sample_rate
            except:
                sampling_duration = 0
            if status in [0]:  # device is off
                timestamp =  next_acquisition - sampling_duration - warmup_duration + activation_delay
                task = "on"
                self.add_event(timestamp, device, task)
            elif status == 1:  # device is on / warming up
                if not device.split(".")[1] in constants.SCHEDULER:
                    data_aquisition_interval = constants.DATA_ACQUISITION_INTERVAL
                    next_acquisition = now - now % data_aquisition_interval + data_aquisition_interval
                    timestamp = next_acquisition - sampling_duration + activation_delay
                    task = "log"
                    self.add_event(timestamp, device, task)
                else:
                    if not "log" in constants.SCHEDULER[device.split(".")[1]]:
                        data_aquisition_interval = constants.DATA_ACQUISITION_INTERVAL
                        next_acquisition = now - now % data_aquisition_interval + data_aquisition_interval
                        timestamp = next_acquisition - sampling_duration + activation_delay
                        task = "log"
                        self.add_event(timestamp, device, task)
                    for event in constants.SCHEDULER[device.split(".")[1]]:
                        data_aquisition_interval = int(constants.SCHEDULER[device.split(".")[1]][event])
                        next_acquisition = now - now % data_aquisition_interval + data_aquisition_interval
                        timestamp = next_acquisition - sampling_duration + activation_delay
                        task = event
                        self.add_event(timestamp, device, task)
            elif status == 2:  # device is ready / acquiring data
                timestamp =  next_acquisition + activation_delay
                '''if data_aquisition_interval - sampling_duration - warmup_duration == 0:
                    task = "on"
                else:
                    task = "off'''
                task = "off"
                self.add_event(timestamp, device, task)

    def add_event(self, timestamp, device, task):
        """Adds an event {timestamp:{device1:[task1, task2,...],...} to the event table.

        Params:
            timestamp(int)
            device(str)
            task(str)
        """
        if timestamp in self.event_table:
            if device in self.event_table[timestamp]:
                self.event_table[timestamp][device].append(task)
            else:
                self.event_table[timestamp][device]=[task]
        else:
            self.event_table[timestamp] = {device:[task]}
