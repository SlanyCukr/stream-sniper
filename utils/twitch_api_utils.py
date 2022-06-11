from twitchAPI import VideoType
from twitchAPI.twitch import Twitch

from database.stream_table_gateway import select_last_twitch_stream_id_db

TWITCH_OBJECT = Twitch('wsasht7hzjpd39lzbdkubk6mn5xzjh', 'cmfky1zvm9rb8dh8jz4ibueuztg7e6')


def get_stream_info(nick):
    stream_info = TWITCH_OBJECT.get_streams(user_login=[nick])['data']

    return stream_info


def get_creator_twitch_id(nick):
    response = TWITCH_OBJECT.get_users(logins=[nick])
    return response['data'][0]['id']


def find_available_video_ids(nickname: str) -> []:
    twitch_user_id = get_creator_twitch_id(nickname)
    videos = TWITCH_OBJECT.get_videos(user_id=twitch_user_id, video_type=VideoType.ARCHIVE)['data']

    return videos


def find_suitable_video_id(nickname: str) -> int:
    twitch_user_id = get_creator_twitch_id(nickname)
    videos = TWITCH_OBJECT.get_videos(user_id=twitch_user_id, video_type=VideoType.ARCHIVE)

    # selects last processed stream
    last_stream_id = select_last_twitch_stream_id_db(nickname)

    # just use first video_id, if it isn't already processed
    processed_video = videos['data'][0]
    """ if last_stream_id:
        processed_video = list(filter(lambda x:
                                      twitch_datetime_str_to_datetime(x['created_at']) > last_stream_start and
                                      int(x['stream_id']) != last_stream_id
                                      , videos['data'])"""