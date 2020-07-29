FROM python:3.8-buster

EXPOSE 5000
VOLUME ["/share", "/archive"]

WORKDIR /app

RUN curl -o gphoto2-updater.sh -L "https://raw.githubusercontent.com/gonzalo/gphoto2-updater/master/gphoto2-updater.sh" \
    && chmod +x gphoto2-updater.sh \
    && ./gphoto2-updater.sh -s

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . ./

CMD [ "python", "webapp.py", "--verbose" ]