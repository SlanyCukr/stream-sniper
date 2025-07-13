from typing import List, Optional, Dict, Any
from datetime import datetime

import uvicorn as uvicorn
from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from ..database.chatter_table_gateway import select_all_chatters_on_stream_db
from ..database.creator_table_gateway import select_creators_db
from ..database.message_table_gateway import select_chatter_messages_db, select_chatter_id_db
from ..database.stream_table_gateway import select_all_streams_db, select_stream_comprehensive_db, \
    select_most_active_chatters_db, select_most_tagged_chatters_db, select_creators_that_wrote_in_stream_db, \
    select_chatters_in_stream_db, select_chatter_messages_on_stream_db, select_all_stream_count_db

load_dotenv()

# Pydantic Models for API Documentation
class Creator(BaseModel):
    """Twitch creator/streamer information"""
    id: int = Field(..., description="Unique creator ID", example=1)
    display_name: str = Field(..., description="Creator's display name on Twitch", example="SomeStreamer")

class Chatter(BaseModel):
    """Chat participant information"""
    id: int = Field(..., description="Unique chatter ID", example=1)
    nick: str = Field(..., description="Chatter's nickname", example="viewer123")

class ChatterID(BaseModel):
    """Chatter ID response"""
    id: int = Field(..., description="Unique chatter ID", example=1)

class Message(BaseModel):
    """Chat message information"""
    text: str = Field(..., description="Message content", example="Hello chat!")
    timestamp: str = Field(..., description="Message timestamp", example="2024-01-15 20:30:15")

class StreamBasic(BaseModel):
    """Basic stream information"""
    id: int = Field(..., description="Unique stream ID", example=1)
    display_name: str = Field(..., description="Stream title/display name", example="Epic Gaming Session")
    start: str = Field(..., description="Stream start time", example="2024-01-15 20:00:00")
    end: str = Field(..., description="Stream end time", example="2024-01-15 23:30:00")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail image URL")
    message_count: int = Field(..., description="Total number of chat messages", example=1250)

class ActiveChatter(BaseModel):
    """Most active chatter statistics"""
    chatter_id: int = Field(..., description="Chatter ID", example=42)
    nick: str = Field(..., description="Chatter nickname", example="chatty_user")
    message_count: int = Field(..., description="Number of messages sent", example=125)

class TaggedChatter(BaseModel):
    """Most tagged chatter statistics"""
    tagged_chatter_id: int = Field(..., description="Tagged chatter ID", example=15)
    nick: str = Field(..., description="Tagged chatter nickname", example="popular_user")
    tag_count: int = Field(..., description="Number of times tagged", example=45)

class StreamComprehensive(BaseModel):
    """Comprehensive stream information with analytics"""
    title: str = Field(..., description="Stream title", example="Epic Gaming Session")
    start: str = Field(..., description="Stream start time", example="2024-01-15 20:00:00")
    end: str = Field(..., description="Stream end time", example="2024-01-15 23:30:00")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail image URL")
    message_count: int = Field(..., description="Total chat messages", example=1250)
    creator_nick: str = Field(..., description="Creator nickname", example="streamer123")
    creator_display_name: str = Field(..., description="Creator display name", example="Amazing Streamer")
    profile_image_url: Optional[str] = Field(None, description="Creator profile image URL")
    creator_id: int = Field(..., description="Creator ID", example=5)

class StreamDetails(BaseModel):
    """Detailed stream analytics response"""
    csi: List[Any] = Field(..., description="Comprehensive stream info tuple")
    mac: List[List[Any]] = Field(..., description="Most active chatters")
    mtc: List[List[Any]] = Field(..., description="Most tagged chatters")
    octw: List[List[Any]] = Field(..., description="Other creators that wrote in stream")
    cis: List[List[Any]] = Field(..., description="Chatters in stream")

class StreamsResponse(BaseModel):
    """Paginated streams response"""
    streams: List[List[Any]] = Field(..., description="List of stream data tuples")
    max_offset: int = Field(..., description="Maximum offset for pagination", example=1000)

class ErrorResponse(BaseModel):
    """Error response model"""
    detail: str = Field(..., description="Error message", example="Stream not found")

# FastAPI App Configuration
app = FastAPI(
    title="Stream Sniper API",
    description="""
    A comprehensive Twitch stream analytics API that provides access to chat data, 
    stream statistics, and user interaction analytics from Twitch VODs.
    
    ## Features
    
    * **Stream Analytics**: Get detailed information about Twitch streams including message counts, duration, and metadata
    * **Chat Analysis**: Access chat messages, most active chatters, and interaction patterns
    * **Creator Insights**: Track creator participation across different streams
    * **User Analytics**: Analyze individual chatter behavior and message history
    * **Tagging Analytics**: Discover most mentioned/tagged users in chat
    
    ## Data Source
    
    All data is collected from publicly available Twitch VOD chat logs and processed 
    to provide meaningful analytics and insights.
    """,
    version="1.0.0",
    contact={
        "name": "Stream Sniper",
        "url": "https://github.com/your-repo/stream-sniper",
    },
    license_info={
        "name": "MIT",
    },
    servers=[
        {
            "url": "http://localhost:5002",
            "description": "Development server"
        }
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tags for endpoint organization
tags_metadata = [
    {
        "name": "Chatters",
        "description": "Operations related to chat participants and their messages"
    },
    {
        "name": "Streams",
        "description": "Stream information, analytics, and chat data"
    },
    {
        "name": "Creators",
        "description": "Twitch creator/streamer information"
    }
]


@app.get(
    "/chatter/{chatter_id}/messages/",
    response_model=List[List[str]],
    tags=["Chatters"],
    summary="Get messages by chatter",
    description="""
    Retrieve all messages sent by a specific chatter across all streams.
    Returns a list of [message_text, timestamp] tuples.
    """,
    responses={
        200: {
            "description": "List of messages with timestamps",
            "content": {
                "application/json": {
                    "example": [
                        ["Hello everyone!", "2024-01-15 20:30:15"],
                        ["Great stream!", "2024-01-15 20:45:22"],
                        ["@streamer keep it up!", "2024-01-15 21:10:03"]
                    ]
                }
            }
        },
        404: {"model": ErrorResponse, "description": "Chatter not found"}
    }
)
def get_chatter_messages(
    chatter_id: int = Path(..., description="Unique chatter ID", example=42)
):
    """Get all messages sent by a specific chatter"""
    try:
        result = select_chatter_messages_db(chatter_id)
        if not result:
            raise HTTPException(status_code=404, detail="Chatter not found or has no messages")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    "/chatter/{nick}/chatter_id",
    response_model=List[int],
    tags=["Chatters"],
    summary="Get chatter ID by nickname",
    description="""
    Look up a chatter's unique ID using their nickname.
    Returns the chatter ID that can be used in other endpoints.
    """,
    responses={
        200: {
            "description": "Chatter ID found",
            "content": {
                "application/json": {
                    "example": [42]
                }
            }
        },
        404: {"model": ErrorResponse, "description": "Chatter not found"}
    }
)
def get_chatter_id(
    nick: str = Path(..., description="Chatter nickname", example="viewer123")
):
    """Get chatter ID by their nickname"""
    try:
        result = select_chatter_id_db(nick)
        if not result:
            raise HTTPException(status_code=404, detail="Chatter not found")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    '/streams/',
    response_model=StreamsResponse,
    tags=["Streams"],
    summary="Get streams with pagination",
    description="""
    Retrieve streams for a specific creator with pagination support.
    Use creator_id = -1 to get streams from all creators.
    
    Each stream in the response contains:
    - Stream ID
    - Display name/title
    - Start time
    - End time
    - Thumbnail URL
    - Message count
    """,
    responses={
        200: {
            "description": "Paginated list of streams",
            "content": {
                "application/json": {
                    "example": {
                        "streams": [
                            [1, "Epic Gaming Session", "2024-01-15 20:00:00", "2024-01-15 23:30:00", "https://example.com/thumb.jpg", 1250],
                            [2, "Chill Stream", "2024-01-14 18:00:00", "2024-01-14 22:00:00", "https://example.com/thumb2.jpg", 856]
                        ],
                        "max_offset": 1000
                    }
                }
            }
        },
        400: {"model": ErrorResponse, "description": "Invalid parameters"}
    }
)
def get_streams(
    creator_id: int = Query(..., description="Creator ID (use -1 for all creators)", example=5),
    offset: int = Query(0, description="Pagination offset", example=0, ge=0)
):
    """Get paginated list of streams for a creator"""
    try:
        streams = select_all_streams_db(creator_id, offset)
        max_offset = select_all_stream_count_db(creator_id)
        return {"streams": streams, "max_offset": max_offset}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    '/stream/{stream_id}/chatters',
    response_model=List[List[Any]],
    tags=["Streams"],
    summary="Get all chatters in a stream",
    description="""
    Retrieve all unique chatters who participated in a specific stream.
    Returns chatter information including their IDs and nicknames.
    """,
    responses={
        200: {
            "description": "List of chatters in the stream",
            "content": {
                "application/json": {
                    "example": [
                        [42, "viewer123"],
                        [15, "chatty_user"],
                        [87, "stream_regular"]
                    ]
                }
            }
        },
        404: {"model": ErrorResponse, "description": "Stream not found"}
    }
)
def get_stream_chatters(
    stream_id: int = Path(..., description="Unique stream ID", example=1)
):
    """Get all chatters who participated in a stream"""
    try:
        result = select_all_chatters_on_stream_db(stream_id)
        if not result:
            raise HTTPException(status_code=404, detail="Stream not found or has no chatters")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    '/stream/{stream_id}/',
    response_model=StreamDetails,
    tags=["Streams"],
    summary="Get comprehensive stream analytics",
    description="""
    Get detailed analytics and information for a specific stream.
    
    Returns comprehensive data including:
    - **csi**: Comprehensive stream info (title, times, creator details)
    - **mac**: Most active chatters (top 3 by message count)
    - **mtc**: Most tagged chatters (top 3 by tag mentions)
    - **octw**: Other creators who wrote in this stream
    - **cis**: Count of unique chatters in stream
    
    This endpoint provides a complete analytics overview of stream chat activity.
    """,
    responses={
        200: {
            "description": "Comprehensive stream analytics",
            "content": {
                "application/json": {
                    "example": {
                        "csi": ["Epic Gaming Session", "2024-01-15 20:00:00", "2024-01-15 23:30:00", "https://thumb.jpg", 1250, "streamer123", "Amazing Streamer", "https://profile.jpg", 5],
                        "mac": [[42, "chatty_user", 125], [15, "regular_viewer", 89], [7, "stream_fan", 76]],
                        "mtc": [[15, "popular_user", 45], [23, "famous_chatter", 32], [11, "mentioned_user", 28]],
                        "octw": [[99, "other_streamer"], [101, "guest_creator"]],
                        "cis": [[287]]
                    }
                }
            }
        },
        404: {"model": ErrorResponse, "description": "Stream not found"}
    }
)
def get_stream(
    stream_id: int = Path(..., description="Unique stream ID", example=1)
):
    """Get comprehensive analytics for a specific stream"""
    try:
        comprehensive_stream_info = select_stream_comprehensive_db(stream_id)
        if not comprehensive_stream_info:
            raise HTTPException(status_code=404, detail="Stream not found")
            
        most_active_chatters = select_most_active_chatters_db(stream_id)
        most_tagged_chatters = select_most_tagged_chatters_db(stream_id)
        other_creators_that_wrote = select_creators_that_wrote_in_stream_db(stream_id, comprehensive_stream_info[8])
        chatters_in_stream = select_chatters_in_stream_db(stream_id)

        return {
            "csi": comprehensive_stream_info,
            "mac": most_active_chatters,
            "mtc": most_tagged_chatters,
            "octw": other_creators_that_wrote,
            "cis": chatters_in_stream,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    '/stream/{stream_id}/chatter/{chatter_id}/messages',
    response_model=List[str],
    tags=["Streams"],
    summary="Get chatter messages in specific stream",
    description="""
    Retrieve all messages sent by a specific chatter during a particular stream.
    This is useful for analyzing individual user participation in specific streams.
    """,
    responses={
        200: {
            "description": "List of messages from the chatter in this stream",
            "content": {
                "application/json": {
                    "example": [
                        "Hello everyone!",
                        "Great play!",
                        "@streamer that was amazing!",
                        "Thanks for the stream!"
                    ]
                }
            }
        },
        404: {"model": ErrorResponse, "description": "Stream or chatter not found"}
    }
)
def get_chatter_messages_on_stream(
    stream_id: int = Path(..., description="Unique stream ID", example=1),
    chatter_id: int = Path(..., description="Unique chatter ID", example=42)
):
    """Get messages from a specific chatter in a specific stream"""
    try:
        result = select_chatter_messages_on_stream_db(stream_id, chatter_id)
        if not result:
            raise HTTPException(status_code=404, detail="No messages found for this chatter in this stream")
        return [message[0] for message in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    '/creators',
    response_model=List[List[Any]],
    tags=["Creators"],
    summary="Get all creators",
    description="""
    Retrieve a list of all Twitch creators/streamers in the database.
    Each creator entry contains their ID and display name.
    """,
    responses={
        200: {
            "description": "List of all creators",
            "content": {
                "application/json": {
                    "example": [
                        [1, "Amazing Streamer"],
                        [2, "Pro Gamer"],
                        [3, "Chat Master"],
                        [4, "Stream Legend"]
                    ]
                }
            }
        }
    }
)
def get_creators():
    """Get all creators in the database"""
    try:
        result = select_creators_db()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


# Root endpoint for API information
@app.get(
    "/",
    tags=["API Info"],
    summary="API Information",
    description="Get basic information about the Stream Sniper API"
)
def root():
    """Welcome endpoint with API information"""
    return {
        "name": "Stream Sniper API",
        "version": "1.0.0",
        "description": "Twitch stream analytics API",
        "docs": "/docs",
        "redoc": "/redoc"
    }

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=5001)
