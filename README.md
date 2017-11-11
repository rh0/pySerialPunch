# Python Serial Punch
Proof of concept to output time tracking data from the [punch](https://github.com/adewinter/punch) tracker for [todo.txt](http://todotxt.org/). This output is sent as serial to a [CP2104](https://www.silabs.com/products/development-tools/interface/cp2104-mini-evaluation-kit) chip via USB and rendered on a [sparkfun SerLCD display](https://www.sparkfun.com/products/10097). This was written assuming a Linux system, and will likely need some modifications to runi properly on Windows or MacOS.

## Library Requirements
[Watchdog](https://github.com/gorakhargosh/watchdog)

## config.yml
+ Add the path to your punch.dat file
+ If your punch.dat file is named something else, adjust accordingly
+ If your cp2104 appears at a location other than `/dev/ttyUSB0` adjust serial path
