import logging
import os
import subprocess
import sys

# from twitchio.ext import commands
dumps_chat_path = os.path.join(os.getcwd(), "dumps", "chat")


def save_chat(videoId: str):
    """
    Saves Chat Epically

    `videoId` - The video ID with the Chat to download.\n
    `downloadPath` - The path to save the Chat to.

    """
    logging.info("Getting chat from stream...")
    logging.info("Video ID: {}".format(videoId))

    downloadPath = os.path.join(dumps_chat_path, videoId + ".json")
    logging.info("Download path: {}".format(downloadPath))

    process = subprocess.Popen(
        [
            "twitch-dl",
            "-m ChatDownload",
            "-o {}".format(downloadPath),
            "-u {}".format(videoId),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        shell=True,
    )

    while True:
        output = process.stdout.readline()
        print(output.strip())
        # Do something else
        return_code = process.poll()
        if return_code is not None:
            print("RETURN CODE", return_code)
            # Process has finished, read rest of the output
            for output in process.stdout.readlines():
                print(output.strip())
            break
    return downloadPath


if __name__ == "__main__":
    args = sys.argv
    videoId = args[1]
    dlpath = args[2]

    save_chat(videoId, dlpath)
