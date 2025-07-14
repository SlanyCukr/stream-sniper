import requests
import json
from tqdm import tqdm

fetched_emotes = {}

offset = 0
for _ in tqdm(iter(int, 1)):
    response = requests.get(f"https://api.betterttv.net/3/emotes/shared/top?offset={offset}&limit=100")
    
    new_emotes = json.loads(response.text)
    if not new_emotes:
        break

    for emote in new_emotes:
        emote = emote['emote']
        emote_id = emote['id']
        emote_code = emote['code']
        fetched_emotes[emote_code] = emote_id 

    offset += 100

with open("src/bettertv_emotes.js", "w") as file:
    text = f"""/* eslint-disable max-lines */
    const EMOTES_STR = '{json.dumps(fetched_emotes)}'
    const EMOTES = JSON.parse(EMOTES_STR)
    export default EMOTES
    """
    file.write(text)