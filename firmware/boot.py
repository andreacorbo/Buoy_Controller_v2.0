# boot.py -- runs on boot-up
import pyb
import uos
pyb.freq(84000000)  # Sets main clock to reduce power consumption.
pyb.usb_mode("VCP") # Sets usb device to act only as serial, needed to map pyboard to static dev on linux systems.
try:
    uos.mount(pyb.SDCard(), "/sd")
except:
    print("UNABLE TO MOUNT SD")
