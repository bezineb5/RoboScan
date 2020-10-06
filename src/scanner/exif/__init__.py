import pathlib


def get_analogexif_config() -> pathlib.Path:
    base_dir = pathlib.Path(__file__).parent.absolute()
    return base_dir / "analogexif.config"
