import os
import re
import sys
import xml.etree.ElementTree as ET

import ffmpeg
import requests

# You can download an "episode" or a "video"
download_type = "episode"

# You can download subtitle file-type "ttml" and "vtt" or "both"
subtitle_type = "ttml"

MGID = "mgid:arc:promotion:nick.com:0cdfdb4d-ab75-45a4-9ee0-a5ec3205c248"


def format_name(name, include_segment=False):
    name = re.sub(r"[<>:\/|?*]", " ", name)
    if '"' in name:
        quoted = name[name.index('"') + 1:name.rindex('"')]
        if include_segment:
            name = quoted + name[name.rindex('"') + 1:]
        else:
            name = quoted
    return " ".join(name.split())


class Episode:
    def __init__(self, show, item):
        self.show = show
        self.name = item["title"]
        self.mgid = item["mgid"]

    @staticmethod
    def _download_item(url, output):
        item = requests.get(url, params={
            "acceptMethods": "hls",
            "format": "json",
        }).json()["package"]["video"]["item"][0]
        src = item["rendition"][-1]["src"]
        if "transcript" in item:
            if subtitle_type == "both":
                for f in range(2):
                    sub_type = ["ttml", "vtt"]
                    subtitles = next(i for i in item["transcript"][0]["typographic"] if i["format"] == sub_type[int(f)])
                    with open(f"{output}." + sub_type[f], "w", encoding="utf-8") as file:
                        file.write(requests.get(subtitles["src"]).text)
            else:
                subtitles = next(i for i in item["transcript"][0]["typographic"] if i["format"] == subtitle_type)
                with open(f"{output}." + subtitle_type, "w", encoding="utf-8") as file:
                    file.write(requests.get(subtitles["src"]).text)
        print(src)
        ffmpeg.input(src).output(f"{output}.mp4", vcodec="copy").overwrite_output().run()

    def download(self):
        dirname = os.path.join(self.show.name, format_name(self.name))
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        root = ET.fromstring(requests.get("http://udat.mtvnservices.com/service1/dispatch.htm", params={
            "feed": "nick_arc_player_prime",
            "mgid": self.mgid,
        }).text)
        namespace = {"media": "http://search.yahoo.com/mrss/"}
        thumbnail = root.find(".//image/url", namespace).text
        for item in root.findall(".//item"):
            url = item.find("media:group/media:content", namespace).get("url")
            title = format_name(item.find("media:group/media:title", namespace).text, True)
            self._download_item(url, os.path.join(dirname, title))

    def __str__(self):
        return self.name


class Show:
    def __init__(self, item):
        self.name = item["title"]
        self.links = item["links"]

    @classmethod
    def get_shows(cls, mgid):
        items = requests.get(f"http://api.playplex.viacom.com/feeds/networkapp/intl/promolist/1.9/{mgid}", params={
            "platform": "android",
            "brand": "nick",
            "version": "18.21.1",
            "region": "us",
            "key": "networkapp1.0",
        }).json()["data"]["items"]
        for item in items:
            if item["entityType"] == "series":
                yield cls(item)

    def get_episodes(self):
        try:
            items = requests.get(self.links[download_type]).json()["data"]["items"]
        except KeyError:
            sys.exit("Currently no " + download_type + " is available")
        for item in items:
            yield Episode(self, item)

    def __str__(self):
        return self.name


def choose(items, name):
    items = list(items)
    for i, item in enumerate(items, 1):
        print(f"{i}. {item}")
    return items[int(input(f"Which {name}? ")) - 1]


def main():
    show = choose(Show.get_shows(MGID), "show")
    episode = choose(show.get_episodes(), download_type)
    episode.download()


if __name__ == "__main__":
    main()
