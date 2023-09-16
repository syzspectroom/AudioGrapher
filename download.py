from __future__ import unicode_literals
import os
import argparse
import youtube_dl

import whisper
import threading
import queue

from tqdm import tqdm
from termcolor import colored


pbar = None
print_lock = threading.Lock()

class Config:
    def __init__(self):
        # Default values
        self.DOWNLOADS_DIR = 'downloads'
        self.TRANSCRIPTION_DIR = 'transcription'
        self.INPUT_FILE = 'video_links.txt'
        self.THREAD_QUEUE_SIZE = 5
        self.LANGUAGE = 'uk'
        self.MODEL = 'large'

    def update_from_args(self, args):
        self.DOWNLOADS_DIR = args.downloads_dir
        self.TRANSCRIPTION_DIR = args.transcription_dir
        self.INPUT_FILE = args.filename
        self.THREAD_QUEUE_SIZE = args.queue_size
        self.LANGUAGE = args.language
        self.MODEL = args.model

class MyLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)

def print_status(video_id, status, message, color='white'):
    global pbar
    msg = colored(f"[{video_id}] {status} ", color) + message
    if pbar:
        with print_lock:
            pbar.write(msg)
    else:
        print(msg)

def generate_filenames(link, config):
    video_id = link.split('=')[-1]
    audio_file_path = f'{config.DOWNLOADS_DIR}/{video_id}.mp3'
    transcription_file = f'{config.TRANSCRIPTION_DIR}/{video_id}.txt'
    return audio_file_path, transcription_file


def download_audio(link, audio_file_path):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'logger': MyLogger(),
        'outtmpl': audio_file_path,  # Directly use the given filename
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([link])


def transcribe_audio(q, model, language):
    while True:
        audio_file_path, transcription_file_path, pbar = q.get()
        if audio_file_path == "STOP":
            break

        video_id = os.path.basename(audio_file_path).replace('.mp3', '')
        print_status(video_id, '🎙️  Transcribing', "", 'cyan')
        
        # we should set language to None to enable autodetection (slow)
        if language == "auto":
            language = None

        result = model.transcribe(audio_file_path, language=language)
        with open(transcription_file_path, 'w') as out_file:
            out_file.write(result['text'])
        with print_lock:
            pbar.update(1)
        print_status(video_id, '✔️  Transcription Saved', f"to {transcription_file_path}", 'green')


def main():
    config = Config()
    parser = argparse.ArgumentParser(description='YouTube Video Transcription')
    parser.add_argument('filename', nargs='?', default=config.INPUT_FILE,
                    help='Input file containing video links')
    parser.add_argument('--downloads-dir', default=config.DOWNLOADS_DIR,
                        help='Directory for downloaded audio files')
    parser.add_argument('--transcription-dir', default=config.TRANSCRIPTION_DIR,
                        help='Directory for transcription files')
    parser.add_argument('--queue-size', type=int, default=config.THREAD_QUEUE_SIZE,
                        help='Max size for the threading queue')
    parser.add_argument('--language', default=config.LANGUAGE,
                    help='Language for transcription or "auto" for automatic detection')
    parser.add_argument('--model', default=config.MODEL,
                        help='Model for transcription. Available: "large", "medium", "small", "base", "tiny"')

    args = parser.parse_args()
    config.update_from_args(args)

    run(config)


def run(config):
    global pbar

    # Create Directories
    if not os.path.exists(config.DOWNLOADS_DIR):
        os.makedirs(config.DOWNLOADS_DIR)

    if not os.path.exists(config.TRANSCRIPTION_DIR):
        os.makedirs(config.TRANSCRIPTION_DIR)

    model = whisper.load_model(config.MODEL)
    q = queue.Queue(maxsize=config.THREAD_QUEUE_SIZE)

    # Start transcribing thread
    transcribe_thread = threading.Thread(
        target=transcribe_audio, args=(q, model, config.LANGUAGE))
    transcribe_thread.start()

    with open(config.INPUT_FILE, 'r') as file:
        links = file.readlines()
        with tqdm(total=len(links), desc="Overall Progress", ncols=100, position=1, leave=True) as pbar:
            for link in links:
                link = link.strip()
                video_id = link.split('=')[-1]

                audio_file_path, transcription_file_path = generate_filenames(
                    link, config)

                if os.path.exists(transcription_file_path):
                    with print_lock:
                        pbar.update(1)
                    print_status(video_id, '⚠️  Skipped', f"Transcription already exists.", 'yellow')
                    continue

                print_status(video_id, '⬇️  Downloading', f"from {link}", 'blue')
                try:
                    if not os.path.exists(audio_file_path):
                        download_audio(link, audio_file_path)
                    else:
                        print_status(video_id, '⚠️  Download Skipped', f"MP3 file already exists.", 'yellow')
                    q.put((audio_file_path, transcription_file_path, pbar))
                except Exception as e:
                    print_status(video_id, '❌  Error', f"Processing {link}. Error: {e}", 'red')
            pbar.close()

    # Tell the transcribe thread to stop after processing all items in the queue
    q.put(("STOP", "", pbar))
    transcribe_thread.join()


if __name__ == "__main__":
    main()
