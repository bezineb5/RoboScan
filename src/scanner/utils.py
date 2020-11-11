import argparse
import json
from typing import Any, Optional

import requests


def notify_ifttt(ifttt_key: Optional[str], action: str, value1: Any=None, value2: Any=None, value3: Any=None) -> None:
    if not ifttt_key:
        return

    url = f"https://maker.ifttt.com/trigger/{action}/with/key/{ifttt_key}"
    payload = {
        "value1" : value1,
        "value2" : value2,
        "value3" : value3,
    }

    r = requests.post(url, data=json.dumps(payload))
    r.raise_for_status()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Roboscan: Automatic film scanner')

    # Debugging
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose mode')
    parser.add_argument('--dryrun', action='store_true',
                        help='Dry run without camera')

    # Hardware configuration
    parser.add_argument('--pin1', '-p1', default='5', type=int, help='BCM pin for IN1')
    parser.add_argument('--pin2', '-p2', default='6', type=int, help='BCM pin for IN2')
    parser.add_argument('--pin3', '-p3', default='13', type=int, help='BCM pin for IN3')
    parser.add_argument('--pin4', '-p4', default='19', type=int, help='BCM pin for IN4')
    parser.add_argument('--led', '-l', default='26', type=int, help='BCM pin for the LED')
    parser.add_argument('--backlight', '-bl', default='18', type=int, help='BCM pin for the backlight')
    parser.add_argument('--buttonstart', '-s', default='20', type=int, help='BCM pin for the start button')
    parser.add_argument('--buttonskip', '-k', default='21', type=int, help='BCM pin for the skip button')
    parser.add_argument('--infrared', '-ir', action='store_true', help='Use infrared LED')
    parser.add_argument('--use_edge_tpu', '-tpu', action='store_true', help='Use Coral Edge TPU')

    # Storage paths
    parser.add_argument('--destination', '-d', default='/share', type=str, help='Destination path')
    parser.add_argument('--archive', '-a', default='/archive', type=str, help='Archive path')
    parser.add_argument('--temp', '-t', default='/tmp', type=str, help='Temporary path')
    parser.add_argument('--settings', default='/configuration/settings.json', type=str, help='Settings storage file')

    # Web server configuration 
    parser.add_argument('--port', default='5000', type=int, help='Server port to listen to')

    # IFTTT
    parser.add_argument('--ifttt', type=str, help='IFTTT key to call webhooks')

    return parser.parse_args()
