# Rutube-Downloader

A simple media downloader from the website rutube.ru

> [!IMPORTANT]
> FFmpeg is required for the script to work.

## Install

```bash
git clone https://github.com/Ladvix/rutube-downloader.git
cd rutube-downloader
pip install -r requirements.txt
```

## Usage

```python
from rutube_downloader.main import RutubeDownloader

downloader = RutubeDownloader()
downloader.download_video(
    video_id='...', 
    output_filename='video.mp4',
)
```

> [!IMPORTANT]
> By default, the video is downloaded in the best quality.