import base64
import os
import time
from pathlib import Path
from typing import List

import requests
from dotenv import load_dotenv

from src.modules.notifyfirebase.apps import Apps
from src.modules.notifyfirebase.notification import Notification
from src.modules.notifyfirebase.notify_api import NotifyAPI
from src.modules.rss_reader.rss_reader import RssReader

if os.path.exists('.env'):
    dotenv_path = Path('.env')
    load_dotenv(dotenv_path=dotenv_path)

APP_NAME = os.getenv('APP_NAME')
MONGODB_URL = os.getenv('MONGODB_URL')
PORT = os.getenv('PORT', 5000)

if not MONGODB_URL:
    print("MONGODB_URL are not set.")
    print("Exiting RssReader...")
    exit(0)

endpoint = f"http://localhost:{PORT}"
session = requests.Session()
notify_api = NotifyAPI()


def update_timestamp() -> str:
    return time.strftime(
        "%a, %d %b %Y %H:%M:%S -0000",
        time.gmtime()
    )


def get_feeds() -> List[str]:
    feeds = []
    res = session.get(
        url=f"{endpoint}/api/v1/rss/subscriptions"
    )
    if res.status_code == 200:
        for feed in res.json():
            feeds.append(feed['rss_url'])
        print("Rss feeds fetched successfully")
    else:
        print("Error fetching rss feeds")
        print(res.text)

    return feeds


def aria_add(raw_link: str) -> None:
    base64_link = base64.b64encode(raw_link.encode('utf-8'))

    res = session.post(
        url=f"{endpoint}/api/v1/aria/add",
        params={'uri': base64_link}
    )
    if res.status_code == 200:
        print(res.json()['message'])
    else:
        print(f"Error adding magnet link: {res.status_code}")


def rss_add_torrent(feed: dict) -> None:
    title = feed['title']
    link = feed['torrent']
    print(f"RSS Callback: {title} - {link}")

    if link.startswith('magnet') or link.endswith('.torrent'):
        aria_add(link)
        notify_api.notify(
            app=Apps.TORRENTIUM,
            notification=Notification(
                title="New feed",
                body=f"\"{title}\" download started",
                topic=f"rss_{APP_NAME}"
            )
        )
    else:
        print(f"Feed: \"{title}\" does not contain a magnet or torrent link. Skipping...")


if __name__ == "__main__":

    timestamp = update_timestamp()

    while True:
        feeds = get_feeds()
        if len(feeds) == 0:
            print("No feeds found")
        else:
            RssReader(
                urls=feeds,
                last_updated=timestamp,
                callback=rss_add_torrent
            )
        timestamp = update_timestamp()
        # sleep 15 minutes
        time.sleep(15 * 60)
