# AudioGrapher - YouTube Video Transcription Library

A utility to download audio from YouTube videos, transcribe them, and save the transcriptions locally.

## Description

This project allows users to automatically download the audio content of YouTube videos and then transcribe that audio using the Whisper API. The transcriptions are saved locally.

## Requirements

- Python 3.x
- youtube_dl
- whisper

Install the required libraries with:
```bash
$ pip install -r requirements.txt
```

## Usage

1. Prepare a text file containing YouTube video links, one link per line.
2. By default, the script will look for a file named `video_links.txt` in the current directory. However, this can be changed using command line arguments.
3. Run the script:
```bash
$ python download.py [filename]
```
### Command Line Arguments:
- `filename`: Input file containing YouTube video links. Default is `video_links.txt`.
- `--downloads-dir`: Directory for downloaded audio files. Default is `downloads`.
- `--transcription-dir`: Directory for transcription files. Default is `transcription`.
- `--queue-size`: Max size for the threading queue. Default is `5`.
- `--language`: Language for transcription or set to "auto" for automatic detection (which can be slower). Default is `uk`.
- `--model`: Model specification for transcription. Options: "large", "medium", "small", "base", "tiny". Default is `large`

Example:
```bash
python download.py my_video_links.txt --downloads-dir=my_downloads --transcription-dir=my_transcriptions --queue-size=10 --language=en --model=medium
```

## Troubleshooting
### Errors with youtube_dl

If you encounter any issues or errors with `youtube_dl`, it's possible that the version you're using is out of date or has some bugs. To address this, you can update to the nightly version of `youtube_dl` which may have fixes for recent issues. Use the following command to do so:
```bash
pip install 'youtube-dl @ git+https://github.com/ytdl-org/ytdl-nightly'
```
This will install the latest nightly version directly from the official repository. However, note that while the nightly version might have bug fixes, it could also have unstable features. Use it at your discretion.

If the error persists even after updating, you can check the official `youtube_dl` GitHub repository for any open issues related to your problem or consult their documentation.
