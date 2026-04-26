import asyncio
from src.downloader import RutubeDownloader

async def main():
    async with RutubeDownloader() as dl:
        await dl.download_video('') # Paste here video_id

if __name__ == '__main__':
    asyncio.run(main())