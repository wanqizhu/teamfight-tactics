import requests
import shutil
import json


with open('championStats.json') as f:
    data = json.load(f)

for champion in data:
    r = requests.get("https://blitz-cdn.blitz.gg/blitz/tft/champion_squares/set3/%s.png"
         % champion, stream=True)
    if r.status_code == 200:
        with open("imgs/%s.png" % champion, 'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)

        print(champion, "success")
    else:
        print(champion, "failed to fetch", r.status_code)