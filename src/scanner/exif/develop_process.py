"""
List of all photographic development processes.
From: https://en.wikipedia.org/wiki/Category:Photographic_film_processes
"""

from typing import List


PROCESSES = [
    'Ap-41',
    'Black and white negative processing',
    'Black and white reversal processing',
    'C-22',
    'C-41',
    'Cross processing',
    'Cycolor',
    'Dr5 chrome',
    'E-2',
    'E-3',
    'E-4',
    'E-6',
    'Eastman Color Negative',
    'Eastman Color Positive',
    'Ilfochrome',
    'Instant film',
    'Instax',
    'K-14',
    'Lith print',
    'RA-4',
]


def get_develop_processes() -> List[str]:
    return PROCESSES
