from datetime import datetime
from pytimeparse.timeparse import timeparse


def twitch_datetime_str_to_datetime(str_representation):
    return datetime.strptime(str_representation, '%Y-%m-%dT%H:%M:%SZ')


def add_timedelta_to_point_in_time(time_point: datetime, delta: str):
    timestamp_with_delta = time_point.timestamp() + timeparse(delta)
    return datetime.fromtimestamp(timestamp_with_delta)