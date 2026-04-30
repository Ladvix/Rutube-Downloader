import asyncio
from src.downloader import RutubeDownloader

async def main():
    async with RutubeDownloader() as dl:
        await dl.download_video('c6f1e7ede7bcd7a3638975093e89400c', mode='quickly') # Paste here video_id

if __name__ == '__main__':
    asyncio.run(main())