import uvicorn as uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.chatter_table_gateway import select_all_chatters_on_stream_db
from database.message_table_gateway import select_chatter_messages_db, select_chatter_id_db
from database.stream_table_gateway import select_all_streams_db, select_stream_comprehensive_db, \
    select_most_active_chatters_db, select_most_tagged_chatters_db, select_creators_that_wrote_in_stream_db, \
    select_chatters_in_stream_db, select_chatter_messages_on_stream_db

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/chatter/{chatter_id}/messages/")
def get_chatter_messages(chatter_id: int):
    return select_chatter_messages_db(chatter_id)


@app.get("/chatter/{nick}/chatter_id")
def get_chatter_id(nick: str):
    return select_chatter_id_db(nick)


@app.get('/streams')
def get_streams():
    return select_all_streams_db()


@app.get('/stream/{stream_id}/chatters')
def get_stream_chatters(stream_id: int):
    return select_all_chatters_on_stream_db(stream_id)


@app.get('/stream/{stream_id}/')
def get_stream(stream_id: int):
    comprehensive_stream_info = select_stream_comprehensive_db(stream_id)
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


@app.get('/stream/{stream_id}/chatter/{chatter_id}/messages')
def get_chatter_messages_on_stream(stream_id: int, chatter_id: int):
    return select_chatter_messages_on_stream_db(stream_id, chatter_id)


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=5001, debug=True)
