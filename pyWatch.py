import sys
import os
import time
import logging
from threading import Thread
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class PunchDatEvent(FileSystemEventHandler):
    # Flag to stop and start the thread.
    running = False

    # This method is what will be threaded, and will output a count when the
    # thread is active.
    def tick_tock(self):
        tockCount = 0
        while(self.running == True):
            logging.info("Tick Tock %s", tockCount)
            tockCount = tockCount + 1
            time.sleep(.01)

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

    def last_punch_line_complete(self, src_path):
        lastrec = self.get_last_punch_rec(src_path)
        if len(lastrec) == 0:
            isComplete = True
        elif len(lastrec) == 3:
            isComplete = True
        else:
            isComplete = False

        return isComplete

    # Overriding the method provided in FileSystemEventHandler to handle the
    # file modified event punch.dat.
    def on_modified(self, event):
        # Debug to see what values we get in event.
        #logging.info("Triggered event of type %s.", event.event_type)
        #logging.info("Is this a directory? %s", event.is_directory)
        #logging.info("%s, was modified.", event.src_path)

        # Check completion of the last punch task, and trigger the thread if its
        # incomplete.
        if not self.last_punch_line_complete(event.src_path):
            self.running = True
            # Kick off another thread with the timer.
            tickTockThread = Thread(target=self.tick_tock, args=())
            tickTockThread.start()
        else:
            self.running = False


if __name__ == "__main__":
    # Setting up out logging output format.
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s.%(msecs)03d - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    # Make this more reasonable config.
    path = '/home/rho/.todo/data'
    punchDatFilename = 'punch.dat'

    # Instantiate our event handler and observer and kick off the observer thread.
    event_handler = PunchDatEvent()
    observer = Observer()
    observer.schedule(event_handler, path)
    observer.start()
    # A bit of observer delay, and an interrupt for ^C
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logging.info("Observer thread terminated. Goodbye.")
    observer.join()
