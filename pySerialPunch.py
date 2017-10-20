import serial
import time
import logging
import yaml
from threading import Thread
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Load config.
# @TODO add some checks that this is filled out and exists
with open("config.yml", 'r') as ymlfile:
    serCfg = yaml.load(ymlfile)

# A few of the commands for serLCD
COMMAND     = 0xFE
CLEAR       = 0x01
BLINK_ON    = 0x0D
BLINK_OFF   = 0x0C
UL_ON       = 0x0E
UL_OFF      = 0x0C
SET_CUR_L1  = 0x80
SET_CUR_L2  = 0xC0

# Extending FileSystemEventHandler
class PunchDatEvent(FileSystemEventHandler):
    # Flag to stop and start the thread.
    running = False
    lastrec = []

    # Prep the serial connection.
    serLCD = serial.Serial()
    serLCD.baudrate = serCfg['serial']['baud']
    serLCD.port = serCfg['serial']['path']

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

    def tick_tock_stop(self):
        self.lastrec = []
        self.running = False

    # This method is what will be threaded, and will output a count when the
    # thread is active.
    def tick_tock(self):
        self.running = True
        while self.running == True:
            if len(self.lastrec) == 2:
                workingrec = self.lastrec
                if not self.serLCD.is_open:
                    self.serInit()
                if self.serLCD.is_open:
                    self.serCmd(CLEAR)
                    self.serCmd(SET_CUR_L1)
                    self.serWriteString(self.lastrec[0])

                    timestamp = self.lastrec[1]
                    startTime = time.mktime(time.strptime(timestamp[0:15], '%Y%m%dT%H%M%S'))
                    while workingrec == self.lastrec and self.serLCD.is_open:
                        self.serCmd(SET_CUR_L2)
                        self.serWriteString(self.secondsToTime(int(round(time.time() - startTime, 0))))
            else:
                # We've broken out of the while loop so close serial communications.
                self.serClose()
        logging.info("leaving TickTock")
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
        self.lastrec = []

        if not event.is_directory and (event.src_path == serCfg['punch']['path'] + '/' +  serCfg['punch']['filename']):
            # Check completion of the last punch task, and trigger the thread if its
            # incomplete.
            self.lastrec = self.get_last_punch_rec(event.src_path)
            if(len(self.lastrec) != 2):
                self.lastrec = []


if __name__ == "__main__":
    # Setting up out logging output format.
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s.%(msecs)03d - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    # Instantiate our event handler and observer and kick off the observer thread.
    event_handler = PunchDatEvent()
    observer = Observer()
    observer.schedule(event_handler, serCfg['punch']['path'])
    logging.info("Starting punch observer thread.")
    observer.start()
    # A bit of observer delay, and an interrupt for ^C
    # Kick off another thread with the timer.
    tickTockThread = Thread(target=event_handler.tick_tock)
    tickTockThread.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        event_handler.tick_tock_stop()
        observer.stop()
        logging.info("Punch observer thread terminated. Goodbye.")
    observer.join()
