# RoboScan
This is the source code for a Lego+Raspberry Pi-powered analog film roll scanner. Watch it in action:
[![RoboScan](https://yt-embed.herokuapp.com/embed?v=yRDomN48SOs)](https://youtu.be/yRDomN48SOs)

## Parts
You'll need these items to build RoboScan:
* A digital camera with a macro lens: must be compatible with libgphoto2 with image capture and preview support.
* A Raspberry Pi: you may choose a Pi 4 if your camera supports USB 3, otherwise a Pi 2 or 3 is fine.
* A 28BYJ-48 Stepper Motor with Driver: easy to find and cheap (about $6)
* 3D-print an adapter to integrate the stepper motor in the legos: use the stepper mount and axis adapter provided by this project (you'll need some bolts to attach the motor to the adapter): [https://create.arduino.cc/projecthub/fredrikstridsman/lego-stepperbot-df26b9](https://create.arduino.cc/projecthub/fredrikstridsman/lego-stepperbot-df26b9).
* [Adafruit White LED Backlight Module](https://www.adafruit.com/product/1621).
* A LED driver such as [Recom Power RCD-24-0.70/PL/B](https://www.digikey.com/en/products/detail/recom-power/RCD-24-0-70-PL-B/2612677).
* A high-power LED, such as [New Energy LST1-01G03-4095-01](https://www.digikey.com/en/products/detail/new-energy/LST1-01G03-4095-01/9816712): a 4000K white LED, with a CRI (Color Rendering Index) of 95.
* Build the lego part: [https://www.mecabricks.com/en/models/r121kn4gvlB](https://www.mecabricks.com/en/models/r121kn4gvlB).

## Installation
First build the Angular frontend:
```bash
cd scanner-frontend
npm install
ng build --prod
cd ..
```

Then deploy the docker-compose:
```bash
cd docker
# Adjust the hostname to your Raspberry Pi
export DOCKER_HOST=tcp://piscanner:2376 DOCKER_TLS_VERIFY=
docker-compose up -d --build
cd ..
```

## Starting it
The camera must be connected to the Raspberry Pi via USB. It must be compatible with [libgphoto2](www.gphoto.org/proj/libgphoto2/support.php).

## Connect to the web interface
Simply navigate to [http://piscanner/](http://piscanner/) (adjust the hostname to your Raspberry Pi)

## Optional: Google Coral TPU
You can improve the machine learning inference performance by using a [Google Coral Edge TPU USB Accelerator](https://coral.ai/products/accelerator) plugged on a USB port of the Raspberry Pi.
To do so, you have to change the file src/Dockerfile. Replace:
```Dockerfile
CMD ["python", "webapp.py", "--destination", "/storage/share", "--archive", "/storage/archive", "--temp", "/storage/tmp"]
```
by:
```Dockerfile
CMD ["python", "webapp.py", "-tpu", "--destination", "/storage/share", "--archive", "/storage/archive", "--temp", "/storage/tmp"]
```