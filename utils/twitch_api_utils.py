from twitchAPI.twitch import Twitch

TWITCH_OBJECT = Twitch('wsasht7hzjpd39lzbdkubk6mn5xzjh', 'cmfky1zvm9rb8dh8jz4ibueuztg7e6')


def get_stream_info(nick):
    stream_info = TWITCH_OBJECT.get_streams(user_login=[nick])['data']

    return stream_info
