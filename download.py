from __future__ import unicode_literals
import os
import argparse
import youtube_dl

import whisper
import threading
import queue


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


def my_hook(d):
    if d['status'] == 'finished':
        print('Done downloading, now converting ...')


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
        'progress_hooks': [my_hook],
        'outtmpl': audio_file_path,  # Directly use the given filename
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([link])


def transcribe_audio(q, model, language):
    while True:
        audio_file_path, transcription_file_path = q.get()
        if audio_file_path == "STOP":
            break
        print(f"Transcribing audio for {os.path.basename(audio_file_path)}...")
        
        # we should set language to None to enable autodetection (slow)
        if language == "auto":
            language = None

        result = model.transcribe(audio_file_path, language=language)
        with open(transcription_file_path, 'w') as out_file:
            out_file.write(result['text'])
        print(f"Transcription saved to {transcription_file_path}!")


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
        for link in links:
            link = link.strip()

            audio_file_path, transcription_file_path = generate_filenames(
                link, config)

            if os.path.exists(transcription_file_path):
                print(
                    f"Transcription for video ID {os.path.basename(transcription_file_path).replace('.txt', '')} already exists. Skipping...")
                continue

            print(f"Downloading audio from {link}...")
            try:
                if not os.path.exists(audio_file_path):
                    download_audio(link, audio_file_path)
                else:
                    print(
                        f"MP3 File for video ID {os.path.basename(audio_file_path).replace('.mp3', '')} already exists. Skipping download...")
                q.put((audio_file_path, transcription_file_path))
            except Exception as e:
                print(f"Error processing {link}. Error: {e}")

    # Tell the transcribe thread to stop after processing all items in the queue
    q.put(("STOP", ""))
    transcribe_thread.join()


if __name__ == "__main__":
    main()
