"""
Database of films
Data from wikipedia:
https://en.wikipedia.org/wiki/List_of_photographic_films
"""

import csv
import pathlib
from typing import Iterator, Tuple

def get_all_films() -> Iterator[Tuple[str, str]]:
    # Get the film database
    base_dir = pathlib.Path(__file__).parent.absolute()
    filename = base_dir / "films.csv"

    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            yield row['make'], row['name']
