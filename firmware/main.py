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

import machine
import pyb
import utime
import uselect
from pyboard import BOARD
from scheduler import SCHEDULER
from menu import MENU
from tools.session import SESSION
import constants
import _thread
import tools.utils as utils
import gc

for i in reversed(range(5)):  # DEBUG Delays main loop to stop before sleep.
    print("{:> 2d}\" to system startup...".format(i), end="\r")
    utime.sleep(1)
print("\r")

utils.log_file("Reset cause: {}".format(machine.reset_cause()), constants.LOG_LEVEL)  # DEBUG

board = BOARD()  # Creates a board object.

session = SESSION(board=board, timeout=constants.SESSION_TIMEOUT)  # Starts up the remote session.

#_wdt = machine.WDT(timeout=constants.WD_TIMEOUT)  # Startsup the watchdog timer.

scheduler = SCHEDULER()  # Creates the scheduler object.

_poll = uselect.poll()  # Creates a poll object to listen to.
for input in board.input:
    _poll.register(input, uselect.POLLIN)
esc_cnt = 0  # Initializes the escape character counter.

t0 = utime.time()  # Gets timestamp at startup.

while True:
    #_wdt.feed()  # Resets the watchdog timer.
    if board.escaped:
        if not session.loggedin:
            pyb.repl_uart(board.uart)
            _thread.start_new_thread(session.login, (constants.LOGIN_ATTEMPTS,))
            utime.sleep_ms(100)
        else:
            board.prompted = True
        board.escaped = False
    elif session.authenticating:  # Prevents sleeping while user is authenticating.
        if session.loggedin:
            board.prompted = True
            session.authenticating = False
        elif session.loggedout:
            pyb.repl_uart(None)
            session.init()
            session.authenticating = False
    elif board.prompted:  # Prompts user for interactive or file mode.
        if board.set_mode(5):
            if board.interactive:
                menu = MENU(board, scheduler)  # Creates the menu object.
                _thread.start_new_thread(menu.main, ())
            elif board.connected:
                pyb.repl_uart(None)  # Disables repl to avoid byte collision
                _thread.start_new_thread(board.devices[101].receive, (3,))
        board.prompted = False
    elif board.interactive or board.connected:  # Prevents sleeping while user is interacting.
        if session.loggedout:
            pyb.repl_uart(None)  # Disables repl to avoid byte collision
            board.interactive = False
            session.init()
    else:
        poll = _poll.ipoll(0, 0)
        for stream in poll:
            if stream[0].read(1).decode("utf-8") == constants.ESC_CHAR:
                esc_cnt += 1
                if  esc_cnt  == 3:
                    if stream[0] == board.usb:
                        board.prompted = True
                    else:
                        board.escaped = True
                    board.interrupted = False
                    esc_cnt = 0
                    continue

        utime.sleep_ms(100)  # Adds 100ms delay to allow threads startup.
        t0 = utime.time()  # Gets timestamp before sleep.
        if not utils.processes and not board.interrupted and not board.usb.isconnected():  # Waits for no running threads and no usb connetion before sleep.
            if utils.files_to_send():  # Checks for data files to send.
                _thread.start_new_thread(utils.execute, ("quasar_gsmq2403.MODEM_1", ["data_transfer"]))  # Sends data files before sleeping.
            elif scheduler.next_event > t0:
                utils.log_file("Sleeping for {}".format(utils.time_display(scheduler.next_event - t0)), constants.LOG_LEVEL)  # DEBUG
                board.go_sleep(scheduler.next_event - t0)  # Puts board in sleep mode.
                t0 = utime.time()  # Gets timestamp at wakeup.
        board.lastfeed = utime.time()
        #_wdt.feed()  # Resets the watchdog timer.
        scheduler.scheduled(t0)  # Checks out for scheduled events in event table.
    gc.collect()  # Frees ram.
    utils.mem_mon()  # DEBUG
