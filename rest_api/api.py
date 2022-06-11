import uvicorn as uvicorn
from fastapi import FastAPI

from database.chatter_table_gateway import select_all_chatters_on_stream_db
from database.message_table_gateway import select_chatter_messages_db
from database.stream_table_gateway import select_all_streams_db

app = FastAPI()


@app.get("/chatter/{chatter_id}/messages/")
def get_chatter_messages(chatter_id: int):
    return select_chatter_messages_db(chatter_id)


@app.get('/streams')
def get_streams():
    return select_all_streams_db()


@app.get('/stream/{stream_id}/chatters')
def get_stream_chatters(stream_id: int):
    return select_all_chatters_on_stream_db(stream_id)


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=5001, debug=True)
