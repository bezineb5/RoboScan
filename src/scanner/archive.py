import logging
import pathlib
import shutil

log = logging.getLogger(__name__)


class Archive:
    __slots__ = ['archive_path', 'photos_path', ]

    def __init__(self) -> None:
        self.archive_path = pathlib.Path(".")
        self.photos_path = pathlib.Path(".")

    def move_to_archive(self) -> int:
        count = 0

        for f in self.photos_path.glob('*.*'):
            shutil.move(str(f), str(self.archive_path / f.name))
            count += 1
        return count

    def delete_archive(self) -> int:
        count = 0

        for f in self.archive_path.glob('*.*'):
            f.unlink()
            count += 1
        return count
