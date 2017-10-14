import serial
import time
import logging
import yaml
from threading import Thread
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

with open("config.yml", 'r') as ymlfile:
    serCfg = yaml.load(ymlfile)

print(serCfg['serial']['path'])
print(serCfg['punch'])

### @TODO Make this more reasonable config. ###
# Location and name of the punch data file.
path = '/home/rho/.todo/data'
punchDatFilename = 'punch.dat'

# A few of the commands for serLCD
COMMAND     = 0xFE
CLEAR       = 0x01
BLINK_ON    = 0x0D
BLINK_OFF   = 0x0C
UL_ON       = 0x0E
UL_OFF      = 0x0C
SET_CUR_L1  = 0x80
SET_CUR_L2  = 0xC0

# Setup serial vars
usbSerialPath = '/dev/ttyUSB0'
usbSerialBaud = 9600

# Extending FileSystemEventHandler
class PunchDatEvent(FileSystemEventHandler):
    # Flag to stop and start the thread.
    running = False

    # Prep the serial connection.
    serLCD = serial.Serial()
    serLCD.baudrate = usbSerialBaud
    serLCD.port = usbSerialPath

    # Run a serial command.
    def serCmd(self, bits):
        self.serLCD.write(bytes([COMMAND]))
        self.serLCD.write(bytes([bits]))

    # Initialize a serial connection.
    def serInit(self):
        if not self.serLCD.is_open:
            self.serLCD.open()
        if self.serLCD.is_open:
            logging.info("Serial comms open.")
            self.serCmd(CLEAR)
            self.serCmd(BLINK_OFF)
        else:
            logging.info("Unable to open serial comms.")

    # If the serial port is open close it.
    def serClose(self):
        if self.serLCD.is_open:
            self.running = False
            self.serWriteNoTask()
            self.serLCD.close()
            logging.info("Serial comms closed.")

    # Output a string to serial.
    def serWriteString(self, serOutStr):
        for c in str(serOutStr):
            self.serLCD.write(bytes([ord(c)]))

    def serWriteNoTask(self):
        self.serCmd(CLEAR)
        self.serCmd(0x81)
        self.serWriteString("No Active Task")

    def secondsToTime(self, sec):
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        return "%d:%02d:%02d" % (h, m, s)


    # This method is what will be threaded, and will output a count when the
    # thread is active.
    def tick_tock(self, lastreq):
        self.serInit()
        if self.serLCD.is_open:
            self.serCmd(SET_CUR_L1)
            self.serWriteString(lastreq[0])

            timestamp = lastreq[1]
            startTime = time.mktime(time.strptime(timestamp[0:15], '%Y%m%dT%H%M%S'))
            while(self.running == True and self.serLCD.is_open):
                self.serCmd(SET_CUR_L2)
                self.serWriteString(self.secondsToTime(int(round(time.time() - startTime, 0))))
        # We've broken out of the while loop so close serial communications.
        self.serClose()

    # Borrowed and modified from Punch.py
    def get_last_punch_rec(self, src_path):
        lastrec = []
        try:
            self.punchFile = open(src_path, 'r')
            lines = self.punchFile.readlines()
            if( len(lines) > 0):
                lastline = (lines[len(lines)-1]).strip()
                lastrec = lastline.split('\t')
            else:
                lastrec = []
            self.punchFile.close()
        except IOError:
            lastrec = []

        return lastrec

    # Overriding the method provided in FileSystemEventHandler to handle the
    # file modified event punch.dat.
    def on_modified(self, event):
        self.running = False
        time.sleep(.5)
        # Debug to see what values we get in event.
        #logging.info("Triggered event of type %s.", event.event_type)
        #logging.info("Is this a directory? %s", event.is_directory)
        #logging.info("%s, was modified.", event.src_path)

        # Check completion of the last punch task, and trigger the thread if its
        # incomplete.
        lastrec = self.get_last_punch_rec(event.src_path)
        if(len(lastrec) == 2):
            self.running = True
            # Kick off another thread with the timer.
            tickTockThread = Thread(target=self.tick_tock, args=(lastrec,))
            tickTockThread.start()
        else:
            self.running = False


if __name__ == "__main__":
    # Setting up out logging output format.
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s.%(msecs)03d - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    # Instantiate our event handler and observer and kick off the observer thread.
    event_handler = PunchDatEvent()
    observer = Observer()
    observer.schedule(event_handler, path)
    logging.info("Starting punch observer thread.")
    observer.start()
    # A bit of observer delay, and an interrupt for ^C
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        event_handler.serClose()
        observer.stop()
        logging.info("Punch observer thread terminated. Goodbye.")
    observer.join()
