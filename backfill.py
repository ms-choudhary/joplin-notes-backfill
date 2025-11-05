import argparse
import time
import os
import sys
import requests
import html2text
from readability import Document
from urllib.parse import urlparse

JOPLIN_PORT = 41184
TOKEN = os.getenv("JOPLIN_TOKEN")
INBOX_LINKS_ID = "3799cd6846b74411b30afbcdffac8023"
API_BASE = f"http://127.0.0.1:{JOPLIN_PORT}"

def joplin_get(path):
    r = requests.get(f"{API_BASE}{path}")
    r.raise_for_status()
    return r.json()

def joplin_post(path, payload):
    r = requests.post(f"{API_BASE}{path}?token={TOKEN}", json=payload)
    r.raise_for_status()
    return r.json()

def joplin_delete(path):
    print(f"delete: {path}")
    r = requests.delete(f"{API_BASE}{path}?permanent=1&token={TOKEN}")
    r.raise_for_status()
    return True

def is_url(text):
    try:
        parsed = urlparse(text)
        return parsed.scheme in ("http", "https") and parsed.netloc != ""
    except:
        return False

def fetch_page(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    doc = Document(r.text)
    title = doc.short_title()
    body_html = doc.summary()
    body_md = html2text.html2text(body_html)
    return title, body_md

def is_video_url(url):
    return "youtube.com" in url or "youtu.be" in url or "media.ccc.de" in url

def process_links(takeaction):
    notes = joplin_get(f"/folders/{INBOX_LINKS_ID}/notes?fields=id,title,body,deleted_time&token={TOKEN}")["items"]

    for note in notes:
        if note.get("deleted_time") != 0:
            continue

        title = (note.get("title") or "").strip()
        body = (note.get("body") or "").strip()

        # print(f"{title}")
        # print(f"{body[:100]}")

        if title == body[:80] and is_url(body):
            url = body
            print(f"Processing: {url}")

            if not takeaction:
                continue

            try:
                fetched_title, content = fetch_page(url)

                if is_video_url(url):
                    content = url

                new_note = {
                    "title": fetched_title or url,
                    "body": content,
                    "source_url": url,
                    "parent_id": INBOX_LINKS_ID
                }
                joplin_post("/notes", new_note)
                joplin_delete(f"/notes/{note['id']}")
                print(f"Created new note for {url}")
            except Exception as e:
                print(f"Error processing {url}: {e}")

def main():
    process_links()

if __name__ == "__main__":
    if TOKEN == "":
        print("env JOPLIN_TOKEN required")
        sys.exit(1)

    parser = argparse.ArgumentParser(description='Backfill notes')
    parser.add_argument(
        '--action',
        type=bool,
        help='just list the notes'
    )
    args = parser.parse_args()

    process_links(args.action)
