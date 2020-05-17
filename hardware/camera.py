import logging
from datetime import datetime
from pathlib import Path

import gphoto2 as gp

log = logging.getLogger(__name__)


class Camera():
    __slots__ = ['_target_path', '_camera', ]

    def __init__(self, target_path: Path) -> None:
        self._target_path = target_path

        gp.use_python_logging()
        self._camera = gp.Camera()
        self._camera.init()

    def take_photo(self) -> Path:
        start_time = datetime.now()

        log.info('Capturing image')
        file_path = self._camera.capture(gp.GP_CAPTURE_IMAGE)

        log.info('Camera file path: {0}/{1}'.format(file_path.folder, file_path.name))
        target_file = self._target_path / file_path.name

        log.info('Copying image to: %s', target_file)
        camera_file = self._camera.file_get(
            file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL)
        camera_file.save(str(target_file))

        time_elapsed = datetime.now() - start_time 
        log.info('Elapsed capture time (hh:mm:ss.ms): %s', time_elapsed)

        return target_file
    
    def close(self) -> None:
        self._camera.exit()

    def __enter__(self) -> "Camera":
        return self

    def __exit__(self, type, value, traceback):
        self.close()


class FakeCamera(Camera):
    def __init__(self, target_path: Path):
        pass

    def take_photo(self):
        log.info('[Dry-run] Capturing image')
    
    def close(self):
        pass
