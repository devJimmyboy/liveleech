# twitch_liveleech - Copyright 2022 IRLToolkit Inc.

# Usage: twitch_liveleech.py [channel] [dump path] [final path]


from dotenv import load_dotenv

load_dotenv()

import logging


import os
import string
import time
import datetime
import requests
import streamlink
import ffmpeg
import click
from liveleech.s3_up import upload_file, upload_part

twitchClientId = os.getenv("TWITCH_CLIENT_ID")
twitchClientSecret = os.getenv("TWITCH_CLIENT_SECRET")

months = [
    "jan",
    "feb",
    "mar",
    "apr",
    "may",
    "jun",
    "jul",
    "aug",
    "sep",
    "oct",
    "nov",
    "dec",
]
sleepDuration = 45

sl = streamlink.Streamlink()
sl.set_plugin_option("twitch", "disable-hosting", True)
sl.set_plugin_option("twitch", "disable-ads", True)
sl.set_plugin_option("twitch", "disable-reruns", True)


def append_file(fileName, data):
    with open(fileName, "a") as f:
        f.write("\n")
        f.write(data.decode())


def get_channel_title_and_video():
    req = requests.post(
        "https://id.twitch.tv/oauth2/token?client_id={}&client_secret={}&grant_type=client_credentials".format(
            twitchClientId, twitchClientSecret
        )
    )
    if req.status_code != requests.codes.ok:
        logging.warning(
            "Failed to get Twitch app auth token due to HTTP error. Code: {} | Text: {}".format(
                req.status_code, req.text
            )
        )
        return ("UNKNOWN TITLE", "UNKNOWN ID")
    twitchAuthorization = req.json()["access_token"]
    headers = {
        "Client-Id": twitchClientId,
        "Authorization": "Bearer " + twitchAuthorization,
    }
    req = requests.get(
        "https://api.twitch.tv/helix/users?login={}".format(channelName.lower()),
        headers=headers,
    )
    if req.status_code != requests.codes.ok:
        logging.warning(
            "Failed to get Twitch user id due to HTTP error. Code: {} | Text: {}".format(
                req.status_code, req.text
            )
        )
        return ("UNKNOWN TITLE", "UNKNOWN ID")
    channelId = req.json()["data"][0]["id"]
    req = requests.get(
        "https://api.twitch.tv/helix/channels?broadcaster_id={}".format(channelId),
        headers=headers,
    )
    if req.status_code != requests.codes.ok:
        logging.warning(
            "Failed to get channel title due to HTTP error. Code: {} | Text: {}".format(
                req.status_code, req.text
            )
        )
        return ("UNKNOWN TITLE", "UNKNOWN ID")
    data = req.json()
    req = requests.get(
        "https://api.twitch.tv/helix/streams?user_id={}".format(channelId),
        headers=headers,
    )
    if req.status_code != requests.codes.ok:
        logging.warning(
            "Failed to get video Id due to HTTP error. Code: {} | Text: {}".format(
                req.status_code, req.text
            )
        )
        return ("UNKNOWN TITLE", "UNKNOWN ID")
    videoId = req.json()
    return (data["data"][0]["title"], videoId)


def check_generate_path(pathPrefix):
    date = datetime.date.today()
    dir = "{}/{}_{}".format(pathPrefix, months[date.month - 1], date.year)
    if not os.path.exists(dir):
        logging.info("Creating directory: {}".format(dir))
        os.makedirs(dir)


@click.command()
@click.option("--channel")
@click.option(
    "-d",
    "--downloadPath",
    help="Path to download the video to. Defaults to $cwd/channel/",
)
@click.option(
    "-o",
    "--finalPath",
    help="Path to finalize the video to. Defaults to $CWD/vods/$CHANNEL/",
)
@click.option(
    "-m",
    "--mode",
    type=click.Choice(["save", "bucket"], case_sensitive=False),
    default="save",
)
@click.option("-b", "--bucket", help="S3 bucket to upload to")
def watch_for_videos(channel, downloadpath, finalpath, mode: str, bucket: str):
    """Watch for new streams and download them along with chat."""
    logging.basicConfig(
        handlers=[logging.FileHandler("twitch_ll.log"), logging.StreamHandler()],
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [{}] %(message)s".format(channel),
    )
    if not twitchClientId or not twitchClientSecret:
        logging.critical(
            "Missing TWITCH_LIVELEECH_CLIENT_ID or TWITCH_LIVELEECH_CLIENT_SECRET env variable(s)."
        )
        os._exit(1)

    while True:
        logging.info("Sleeping for {} seconds...".format(sleepDuration))
        time.sleep(sleepDuration)
        logging.info("Done.")

        try:
            streams = sl.streams("https://twitch.tv/{}".format(channel))
        except streamlink.exceptions.PluginError:
            logging.error("Failed to fetch stream via streamlink.")
            continue
        if not streams:
            logging.info("No streams are available.")
            continue
        elif "best" not in streams:
            logging.error("`best` stream not available!")
            break
        logging.info("Stream found! Opening ffmpeg...")
        if mode.lower() == "save":
            fullDownloadPath = "{}/{}.flv".format(downloadpath, int(time.time()))
            logging.info("Writing download to: {}...".format(fullDownloadPath))
            stream = ffmpeg.input(streams["best"].url).output(
                fullDownloadPath, vcodec="copy", acodec="aac"
            )
        elif mode.lower() == "bucket":
            fullDownloadPath = "{}/{}.flv".format(channel, int(time.time()))
            sp_bucket = os.getenv("S3_BUCKET", bucket)

        out, err = ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
        append_file("twitch_ll_download.log", err)
        logging.info("Stream ended!")

        check_generate_path(finalpath)

        title, video = get_channel_title_and_video()
        validChars = "-.() %s%s" % (string.ascii_letters, string.digits)
        title = "".join(c for c in title if c in validChars)

        date = datetime.date.today()
        fullPath = "{}/{}_{}/{}_{}_{}.mp4".format(
            finalpath,
            months[date.month - 1],
            date.year,
            date.day,
            title,
            int(time.time()),
        )
        logging.info(
            "Muxing file {} to final path {}".format(fullDownloadPath, fullPath)
        )
        mux = ffmpeg.input(fullDownloadPath).output(
            fullPath, vcodec="copy", acodec="copy"
        )
        out, err = ffmpeg.run(mux, capture_stdout=True, capture_stderr=True)
        append_file("twitch_ll_mux.log", err)
        logging.info("Done.")


if __name__ == "__main__":
    watch_for_videos()
