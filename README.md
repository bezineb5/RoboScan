# RoboScan
This is the source code for a Lego+Raspberry Pi-powered analog film roll scanner. Watch it in action:
[![RoboScan](http://img.youtube.com/vi/FegPnVco0Qc/0.jpg)](https://youtu.be/FegPnVco0Qc)

## Installation
You'll need python3 with pip installed.
First, install gphoto2 using the [gPhoto2 Updater](https://github.com/gonzalo/gphoto2-updater).
Then clone this repository and install the dependencies:
```bash
git clone https://github.com/bezineb5/RoboScan
cd RoboScan
pip3 install -r requirements.txt
```

## Starting it
The camera must be connected to the Raspberry Pi via USB. It must be compatible with [libgphoto2](www.gphoto.org/proj/libgphoto2/support.php).