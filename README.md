# Rutube-Downloader

A simple async media downloader from the website rutube.ru

## Install

```bash
git clone https://github.com/Ladvix/rutube-downloader.git
cd rutube-downloader
pip install -r requirements.txt
```

## Usage

```python
import asyncio
from src.downloader import RutubeDownloader

async def main():
    async with RutubeDownloader() as dl:
        await dl.download_video('') # Paste here video_id

if __name__ == '__main__':
    asyncio.run(main())
```

> [!IMPORTANT]
> By default, the video is downloaded in the best quality.