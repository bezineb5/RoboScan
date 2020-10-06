FROM python:3.8-buster

EXPOSE 5000
VOLUME ["/storage", "/configuration"]

WORKDIR /app

# libgphoto2
RUN curl -o gphoto2-updater.sh -L "https://raw.githubusercontent.com/gonzalo/gphoto2-updater/master/gphoto2-updater.sh" \
    && chmod +x gphoto2-updater.sh \
    && ./gphoto2-updater.sh -s

# ExifTool
RUN apt-get install libimage-exiftool-perl -y

COPY requirements.txt .
RUN pip install -r requirements.txt

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD curl -f http://localhost:5000/ping || exit 1

# Copy Exiftool config to a directory, and set EXIFTOOL_HOME. See https://exiftool.org/faq.html (question 11)
COPY ./scanner/exif/analogexif.config ./.ExifTool_config
ENV EXIFTOOL_HOME=/app

# Python code
COPY . ./
RUN python -m compileall .

CMD ["python", "webapp.py", "--verbose", "--destination", "/storage/share", "--archive", "/storage/archive", "--temp", "/storage/tmp"]