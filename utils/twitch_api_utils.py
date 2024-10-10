from twitchAPI.type import VideoType
from twitchAPI.twitch import Twitch

from database.stream_table_gateway import select_last_twitch_stream_id_db

TWITCH_OBJECT = Twitch('wsasht7hzjpd39lzbdkubk6mn5xzjh', 'cmfky1zvm9rb8dh8jz4ibueuztg7e6')


def get_stream_info(nick):
    stream_info = TWITCH_OBJECT.get_streams(user_login=[nick])['data']

    return stream_info


def get_creator_twitch_id(nick):
    response = TWITCH_OBJECT.get_users(logins=[nick])
    return response['data'][0]['id']


def get_creator_info(nick) -> tuple:
    response = TWITCH_OBJECT.get_users(logins=[nick])
    streamer_info = response['data'][0]

    return streamer_info['display_name'], streamer_info['profile_image_url']


def find_available_video_ids(nickname: str) -> []:
    twitch_user_id = get_creator_twitch_id(nickname)
    videos = TWITCH_OBJECT.get_videos(user_id=twitch_user_id, video_type=VideoType.ARCHIVE)['data']

    return videos