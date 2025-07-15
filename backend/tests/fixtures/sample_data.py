"""
Sample data fixtures for testing.

This module provides standardized test data that can be used across
different test files to ensure consistency and reduce duplication.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any


# Sample creator data
SAMPLE_CREATORS = [
    {
        "nick": "test_streamer_1",
        "display_name": "Test Streamer One",
        "profile_image_url": "https://example.com/profile1.jpg",
        "twitch_id": "123456789",
    },
    {
        "nick": "test_streamer_2",
        "display_name": "Test Streamer Two",
        "profile_image_url": "https://example.com/profile2.jpg",
        "twitch_id": "987654321",
    },
    {
        "nick": "pro_gamer_test",
        "display_name": "Pro Gamer Test",
        "profile_image_url": "https://example.com/profile3.jpg",
        "twitch_id": "555666777",
    },
]


# Sample stream data
def get_sample_streams(creator_id: int = 1) -> List[Dict[str, Any]]:
    """Generate sample stream data for a given creator."""
    base_time = datetime(2024, 1, 15, 20, 0, 0)

    return [
        {
            "twitch_id": "stream_abc123",
            "title": "Epic Gaming Session - Day 1",
            "start_time": base_time,
            "end_time": base_time + timedelta(hours=3, minutes=30),
            "thumbnail_url": "https://example.com/thumbnail1.jpg",
            "message_count": 1250,
            "creator_id": creator_id,
        },
        {
            "twitch_id": "stream_def456",
            "title": "Chill Coding Stream",
            "start_time": base_time + timedelta(days=1),
            "end_time": base_time + timedelta(days=1, hours=4),
            "thumbnail_url": "https://example.com/thumbnail2.jpg",
            "message_count": 856,
            "creator_id": creator_id,
        },
        {
            "twitch_id": "stream_ghi789",
            "title": "Community Game Night",
            "start_time": base_time + timedelta(days=2),
            "end_time": base_time + timedelta(days=2, hours=2, minutes=45),
            "thumbnail_url": "https://example.com/thumbnail3.jpg",
            "message_count": 2103,
            "creator_id": creator_id,
        },
    ]


# Sample chatter data
SAMPLE_CHATTERS = [
    {"nick": "regular_viewer_1"},
    {"nick": "chatty_user"},
    {"nick": "stream_moderator"},
    {"nick": "new_follower"},
    {"nick": "longtime_subscriber"},
    {"nick": "casual_viewer"},
    {"nick": "emoji_lover"},
    {"nick": "question_asker"},
    {"nick": "meme_poster"},
    {"nick": "helpful_user"},
]

# Sample message texts
SAMPLE_MESSAGE_TEXTS = [
    {"text": "Hello everyone!"},
    {"text": "First!"},
    {"text": "Great stream as always!"},
    {"text": "What game are we playing today?"},
    {"text": "PogChamp"},
    {"text": "Kappa"},
    {"text": "5Head"},
    {"text": "OMEGALUL"},
    {"text": "Thanks for the stream!"},
    {"text": "See you next time!"},
    {"text": "@streamer can you play that song again?"},
    {"text": "That was an amazing play!"},
    {"text": "LUL"},
    {"text": "EZ Clap"},
    {"text": "How long have you been streaming?"},
    {"text": "Love the new overlay!"},
    {"text": "What settings do you use?"},
    {"text": "Can you add me on Discord?"},
    {"text": "When is the next stream?"},
    {"text": "Your gameplay is incredible!"},
    {"text": "💜💜💜"},
    {"text": "🎮🎯🏆"},
    {"text": "Keep up the great work!"},
    {"text": "This music is perfect"},
    {"text": "Time for a bathroom break?"},
    {"text": "Hydration check!"},
    {"text": "Posture check!"},
    {"text": "What rank are you?"},
    {"text": "How many hours played?"},
    {"text": "Subscribed! ❤️"},
]


# Sample chat messages for processing tests
def get_sample_chat_messages() -> List[Dict[str, Any]]:
    """Generate realistic chat message data."""
    base_time = 1642287015.0  # Unix timestamp
    messages = []

    message_data = [
        ("regular_viewer_1", "Hello everyone!", 0),
        ("chatty_user", "First!", 5),
        ("stream_moderator", "Welcome to the stream!", 10),
        ("new_follower", "Just followed! Love the content!", 15),
        ("regular_viewer_1", "What game are we playing today?", 30),
        ("emoji_lover", "PogChamp 🎮", 45),
        ("question_asker", "@streamer what settings do you use?", 60),
        ("meme_poster", "OMEGALUL", 75),
        ("helpful_user", "Check the !commands for help", 90),
        ("longtime_subscriber", "Been watching for 2 years! ❤️", 105),
        ("casual_viewer", "This looks fun!", 120),
        ("chatty_user", "@regular_viewer_1 I think it's the new battle royale", 135),
        ("stream_moderator", "Remember to be respectful in chat", 150),
        ("emoji_lover", "5Head strategy", 165),
        ("question_asker", "How long is today's stream?", 180),
    ]

    for author_name, message_text, time_offset in message_data:
        messages.append(
            {"author": {"name": author_name}, "message": message_text, "time_in_seconds": base_time + time_offset}
        )

    return messages


# Sample data for API response testing
SAMPLE_API_RESPONSES = {
    "creators": [[1, "Test Streamer One"], [2, "Test Streamer Two"], [3, "Pro Gamer Test"]],
    "streams": [
        [
            1,
            "Epic Gaming Session - Day 1",
            "2024-01-15 20:00:00",
            "2024-01-15 23:30:00",
            "https://example.com/thumbnail1.jpg",
            1250,
        ],
        [
            2,
            "Chill Coding Stream",
            "2024-01-16 20:00:00",
            "2024-01-17 00:00:00",
            "https://example.com/thumbnail2.jpg",
            856,
        ],
        [
            3,
            "Community Game Night",
            "2024-01-17 20:00:00",
            "2024-01-17 22:45:00",
            "https://example.com/thumbnail3.jpg",
            2103,
        ],
    ],
    "stream_comprehensive": [
        "Epic Gaming Session - Day 1",  # title
        "2024-01-15 20:00:00",  # start_time
        "2024-01-15 23:30:00",  # end_time
        "https://example.com/thumbnail1.jpg",  # thumbnail_url
        1250,  # message_count
        "test_streamer_1",  # creator_nick
        "Test Streamer One",  # creator_display_name
        "https://example.com/profile1.jpg",  # profile_image_url
        1,  # creator_id
    ],
    "most_active_chatters": [
        [5, "chatty_user", 45],  # chatter_id, nick, message_count
        [2, "regular_viewer_1", 32],
        [7, "emoji_lover", 28],
    ],
    "most_tagged_chatters": [
        [1, "test_streamer_1", 15],  # tagged_chatter_id, nick, tag_count
        [5, "chatty_user", 8],
        [2, "regular_viewer_1", 5],
    ],
    "other_creators_in_stream": [[2, "test_streamer_2"], [3, "pro_gamer_test"]],  # creator_id, nick
    "chatters_in_stream": [[125]],  # count of unique chatters
    "chatter_messages": [
        ["Hello everyone!", "2024-01-15 20:05:15"],
        ["What game are we playing today?", "2024-01-15 20:30:15"],
        ["That was an amazing play!", "2024-01-15 21:15:22"],
        ["Thanks for the stream!", "2024-01-15 23:25:18"],
    ],
}

# Unicode test data
UNICODE_TEST_DATA = {
    "creators": [
        {
            "nick": "unicode_streamer",
            "display_name": "Unicode Streamer 🎮",
            "profile_image_url": "https://example.com/unicode_profile.jpg",
            "twitch_id": "999888777",
        }
    ],
    "streams": [
        {
            "twitch_id": "unicode_stream_001",
            "title": "游戏直播 Gaming Stream 🎯 مرحبا",
            "start_time": datetime(2024, 1, 20, 19, 0, 0),
            "end_time": datetime(2024, 1, 20, 22, 30, 0),
            "thumbnail_url": "https://example.com/unicode_thumb.jpg",
            "message_count": 500,
        }
    ],
    "chatters": [
        {"nick": "viewer_中文"},
        {"nick": "user_العربية"},
        {"nick": "гamer_русский"},
        {"nick": "player_日本語"},
    ],
    "messages": [
        {"text": "Hello! 😀🎮💜"},
        {"text": "你好世界 How are you?"},
        {"text": "مرحبا بك في البث"},
        {"text": "こんにちは！楽しいです"},
        {"text": "Привет! Отличная игра!"},
        {"text": "★☆♦♣♠♥ Special symbols"},
        {"text": "Emoji party: 🎉🎊🎈🎁🎂"},
        {"text": "Math symbols: ∑∏∫∆∇∞"},
        {"text": "Currency: $€£¥₹₿"},
        {"text": "Arrows: ←↑→↓↔↕⬆⬇"},
    ],
}


# Performance test data generators
def generate_large_dataset(
    num_creators: int = 10,
    num_streams_per_creator: int = 20,
    num_chatters: int = 1000,
    num_messages_per_stream: int = 5000,
) -> Dict[str, List]:
    """Generate large dataset for performance testing."""
    creators = []
    streams = []
    chatters = []
    messages = []

    # Generate creators
    for i in range(num_creators):
        creators.append(
            {
                "nick": f"perf_creator_{i}",
                "display_name": f"Performance Creator {i}",
                "profile_image_url": f"https://example.com/perf_profile_{i}.jpg",
                "twitch_id": f"perf_twitch_{i:06d}",
            }
        )

    # Generate chatters
    for i in range(num_chatters):
        chatters.append({"nick": f"perf_chatter_{i}"})

    # Generate streams and messages
    base_time = datetime(2024, 1, 1, 12, 0, 0)

    for creator_idx in range(num_creators):
        for stream_idx in range(num_streams_per_creator):
            stream_start = base_time + timedelta(days=creator_idx * num_streams_per_creator + stream_idx)

            stream = {
                "twitch_id": f"perf_stream_{creator_idx}_{stream_idx}",
                "title": f"Performance Stream {stream_idx} by Creator {creator_idx}",
                "start_time": stream_start,
                "end_time": stream_start + timedelta(hours=3),
                "thumbnail_url": f"https://example.com/perf_thumb_{creator_idx}_{stream_idx}.jpg",
                "message_count": num_messages_per_stream,
                "creator_id": creator_idx + 1,  # Assuming 1-based IDs
            }
            streams.append(stream)

            # Generate messages for this stream
            for msg_idx in range(num_messages_per_stream):
                chatter_idx = msg_idx % num_chatters  # Distribute messages across chatters

                message = {
                    "text": f"Performance message {msg_idx} in stream {stream_idx} by creator {creator_idx}",
                    "chatter_nick": f"perf_chatter_{chatter_idx}",
                    "stream_twitch_id": stream["twitch_id"],
                    "timestamp": stream_start + timedelta(minutes=msg_idx // 10),  # Spread messages over time
                }
                messages.append(message)

    return {"creators": creators, "streams": streams, "chatters": chatters, "messages": messages}


# Error condition test data
ERROR_TEST_DATA = {
    "invalid_creator_data": [
        {"display_name": "No Nick Creator", "twitch_id": "111"},  # Missing nick
        {"nick": "", "display_name": "Empty Nick", "twitch_id": "222"},  # Empty nick
        {"nick": None, "display_name": "Null Nick", "twitch_id": "333"},  # Null nick
    ],
    "invalid_stream_data": [
        {"title": "No Twitch ID Stream", "creator_id": 1},  # Missing twitch_id
        {"twitch_id": "", "title": "Empty Twitch ID", "creator_id": 1},  # Empty twitch_id
        {"twitch_id": "stream_123", "title": "No Creator", "creator_id": 999},  # Non-existent creator
    ],
    "invalid_message_data": [
        {"chatter_id": 999, "stream_id": 1, "message_text_id": 1},  # Non-existent chatter
        {"chatter_id": 1, "stream_id": 999, "message_text_id": 1},  # Non-existent stream
        {"chatter_id": 1, "stream_id": 1, "message_text_id": 999},  # Non-existent message text
    ],
}


# Test data validation helpers
def validate_creator_data(creator_data: Dict[str, Any]) -> bool:
    """Validate creator data structure."""
    required_fields = ["nick", "display_name", "twitch_id"]
    return all(field in creator_data for field in required_fields)


def validate_stream_data(stream_data: Dict[str, Any]) -> bool:
    """Validate stream data structure."""
    required_fields = ["twitch_id", "title"]
    return all(field in stream_data for field in required_fields)


def validate_chatter_data(chatter_data: Dict[str, Any]) -> bool:
    """Validate chatter data structure."""
    return "nick" in chatter_data


def validate_message_data(message_data: Dict[str, Any]) -> bool:
    """Validate message data structure."""
    return "text" in message_data
