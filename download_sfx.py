import urllib.request
import json
import os
import urllib.parse
import time

def fetch_sound(search_term, filename):
    print(f"Searching for '{search_term}'...")
    url = f"https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(search_term + ' filetype:audio')}&srlimit=5&format=json"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 SankofaApp/1.0'})
    
    try:
        response_body = urllib.request.urlopen(req).read().decode()
    except Exception as e:
        print(f"  Search failed: {e}")
        return
        
    data = json.loads(response_body)
    
    if not data.get('query', {}).get('search'):
        print(f"  No results for '{search_term}'")
        return
        
    for item in data['query']['search']:
        title = item['title']
        if not title.lower().endswith('.ogg') and not title.lower().endswith('.mp3'):
            continue
            
        print(f"  Found title: {title}")
        url2 = f"https://commons.wikimedia.org/w/api.php?action=query&titles={urllib.parse.quote(title)}&prop=imageinfo&iiprop=url&format=json"
        req2 = urllib.request.Request(url2, headers={'User-Agent': 'Mozilla/5.0 SankofaApp/1.0'})
        
        try:
            data2 = json.loads(urllib.request.urlopen(req2).read().decode())
            pages = data2['query']['pages']
            file_url = list(pages.values())[0]['imageinfo'][0]['url']
            
            print(f"  Downloading {file_url} to {filename}")
            req_dl = urllib.request.Request(file_url, headers={'User-Agent': 'Mozilla/5.0 SankofaApp/1.0'})
            with urllib.request.urlopen(req_dl) as f_in, open(filename, 'wb') as f_out:
                f_out.write(f_in.read())
            print("  Done.")
            return # success
        except Exception as e:
            print(f"  Download failed for {title}: {e}")
            
    print("  Exhausted all results.")

os.makedirs("frontend/public/audio", exist_ok=True)

sounds = [
    ("crackling fire", "fire"),
    ("wind howling", "wind"),
    ("jungle rain", "nature"),
    ("market ambience", "market"),
    ("drumming", "drums")
]

for term, name in sounds:
    fetch_sound(term, f"frontend/public/audio/{name}.ogg")
    time.sleep(1) # prevent 429
