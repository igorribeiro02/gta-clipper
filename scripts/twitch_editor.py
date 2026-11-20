"""Ajuda a liberar o download OFICIAL de clipes (quando o streamer te põe como editor).

1. Rode:  TWITCH_CLIENT_ID=... TWITCH_CLIENT_SECRET=... python scripts/twitch_editor.py SEU_LOGIN
2. Abra o link que aparecer, logado na SUA conta da Twitch, e autorize.
   (o redirecionamento pra localhost vai dar erro de página — é normal)
3. Copie o número "TWITCH_EDITOR_ID" e salve como segredo no GitHub.
"""
import os
import sys
import urllib.parse

import requests

cid = os.environ["TWITCH_CLIENT_ID"]
tok = requests.post("https://id.twitch.tv/oauth2/token", data={
    "client_id": cid, "client_secret": os.environ["TWITCH_CLIENT_SECRET"], "grant_type": "client_credentials",
}, timeout=20).json()["access_token"]
login = sys.argv[1]
u = requests.get("https://api.twitch.tv/helix/users", params={"login": login},
                 headers={"Client-Id": cid, "Authorization": f"Bearer {tok}"}, timeout=20).json()["data"][0]

url = "https://id.twitch.tv/oauth2/authorize?" + urllib.parse.urlencode({
    "client_id": cid,
    "redirect_uri": "http://localhost:3000",
    "response_type": "token",
    "scope": "editor:manage:clips",
})
print(f"\nTWITCH_EDITOR_ID = {u['id']}\n")
print("Abra e autorize (logado como", login, "):\n", url)
