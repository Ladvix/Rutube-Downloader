import os
import re
import time
import httpx
import shutil
import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urljoin

class RutubeDownloader():
    def __init__(self):
        self.base_url = 'https://rutube.ru'
        self.api_url = f'{self.base_url}/api'
        self.api_ver = 'v2'
        self.player_ver = '2.109.0'
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36'

        self.headers = {
            'User-Agent': self.user_agent,
            'Origin': self.base_url,
            'Referer': self.base_url
        }

        self.max_parallel = 10

    async def __aenter__(self):
        self.client = httpx.AsyncClient(headers=self.headers, follow_redirects=True)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.client:
            await self.client.aclose()

    async def get_video_data(
        self,
        video_id: str,
        request_params: Optional[Dict] = None
    ) -> Optional[Dict]:
        if not request_params:
            request_params = {
                'no_404': True,
                'referer': self.base_url,
                'pver': self.api_ver,
                'client': 'wdp',
                'mq': 'all', # Media Qualities
                'av1': 1, # Codec AV1
                'ac_client': 'web',
                'ver': self.player_ver,
                'ad_ver': self.api_ver,
                'yclid': None
            }

        try:
            response = await self.client.get(f'{self.api_url}/play/options/{video_id}', params=request_params)
            if response.status_code == 200:
                return response.json()
            else:
                print(f'[{response.status_code}] Unknown error when receiving video options')
                return
        
        except httpx.HTTPError as e:
            print(f'[-] Error getting video options')
            return

    async def get_master_playlist(self, url: str) -> Optional[str]:
        try:
            response = await self.client.get(url)
            if response.status_code == 200:
                return response.text
            else:
                print(f'[{response.status_code}] Unknown error when receiving master playlist')
                return

        except httpx.HTTPError as e:
            print(f'[-] Error getting master playlist')
            return

    def get_best_quality_url(self, master_playlist: str) -> Tuple[Optional[str], Optional[int]]:
        try:
            best_res = 0
            best_bandwidth = 0
            best_url = None

            lines = master_playlist.splitlines()
            for i, line in enumerate(lines):
                if line.startswith('#EXT-X-STREAM-INF'):
                    res_match = re.search(r'RESOLUTION=(\d+)x(\d+)', line)
                    bw_match = re.search(r'BANDWIDTH=(\d+)', line)
                    if res_match and bw_match and i + 1 < len(lines):
                        w, h = int(res_match.group(1)), int(res_match.group(2))
                        bandwidth = int(bw_match.group(1))

                        if w * h > best_res:
                            best_res = w * h
                            best_bandwidth = bandwidth
                            next_line = lines[i+1].strip()
                            best_url = urljoin(master_playlist, next_line)

            return best_url, best_bandwidth

        except Exception as e:
            print(f'[!] Error parsing master playlist: {e}')
            return None, None

    async def download_segments(
        self,
        url: str,
        bandwidth: int,
        video_options: Dict,
        output_filename: str
    ):
        try:
            response = await self.client.get(url)
            if response.status_code == 200:
                raw_segments = response.text
            else:
                print(f'[{response.status_code}] Unknown error when receiving segments')
                return

        except httpx.HTTPError as e:
            print(f'[-] Error receiving segments: {e}')
            return

        segments = [line.strip() for line in raw_segments.splitlines() if line.endswith('.ts')]

        downloaded_bytes = 0
        size = (bandwidth * (video_options['duration'] / 1000)) / (8 * 1024**2)
        time_start = time.perf_counter()
        base_url = urljoin(url.rsplit('/', 1)[0] + '/', '')

        with open(output_filename, 'wb') as f:
            for i, segment_name in enumerate(segments):
                segment_path = f'{base_url}/{segment_name}'

                try:
                    segment_response = await self.client.get(segment_path)
                    if segment_response.status_code == 200:
                        f.write(segment_response.content)
                        downloaded_bytes += len(segment_response.content)

                        elapsed_time = time.perf_counter() - time_start
                        mb = downloaded_bytes / (1024 * 1024)
                        speed = mb / elapsed_time if elapsed_time > 0 else 0
                        print(f'[i] {mb:.2f} MB | Speed: {speed:.2f} MB/s | Segment №{i}/{len(segments)}', end='\r', flush=True)

                except httpx.HTTPError as e:
                    print(f'\n[-] Error downloading segment {i}: {e}')
                    break

    async def download_video(
        self,
        video_id: str,
        mode: Optional[str] = None,
        output_filename: Optional[str] = None
    ):
        video_data = await self.get_video_data(video_id)
        if not video_data:
            print('[-] Video data was not received')
            return

        data = video_data.get('video_balancer') or {}
        master_playlist_url = data.get('default') or ''
        if not master_playlist_url:
            print('[-] Master playlist url was not received')
            return

        master_playlist = await self.get_master_playlist(master_playlist_url)
        if not master_playlist:
            print('[-] Master playlist was not received')
            return

        segments_url, bandwidth = self.get_best_quality_url(master_playlist)

        if not mode:
            await self.download_segments(segments_url, bandwidth, video_data, output_filename if output_filename else f'video_{video_id}.mp4')
        elif mode == 'quickly':
            await self.quickly_download_segments(segments_url, bandwidth, video_data, output_filename if output_filename else f'video_{video_id}.mp4')

    async def stream_segments(
        self,
        url: str
    ):
        try:
            response = await self.client.get(url)
            if response.status_code == 200:
                raw_segments = response.text
            else:
                print(f'[{response.status_code}] Unknown error when receiving segments')
                return

        except httpx.HTTPError as e:
            print(f'[-] Error receiving segments: {e}')
            return

        segments = [line.strip() for line in raw_segments.splitlines() if line.endswith('.ts')]

        base_url = urljoin(url.rsplit('/', 1)[0] + '/', '')

        for i, segment_name in enumerate(segments):
            segment_path = f'{base_url}/{segment_name}'

            try:
                async with self.client.stream('GET', segment_path) as segment_response:
                    if segment_response.status_code == 200:
                        async for chunk in segment_response.aiter_bytes():
                            if chunk: yield chunk

            except httpx.HTTPError as e:
                print(f'\n[-] Error downloading segment {i}: {e}')
                break

    async def stream_video(
        self,
        video_id: str
    ):
        video_data = await self.get_video_data(video_id)
        if not video_data:
            print('[-] Video data was not received')
            return

        data = video_data.get('video_balancer') or {}
        master_playlist_url = data.get('default') or ''
        if not master_playlist_url:
            print('[-] Master playlist url was not received')
            return

        master_playlist = await self.get_master_playlist(master_playlist_url)
        if not master_playlist:
            print('[-] Master playlist was not received')
            return

        segments_url, bandwidth = self.get_best_quality_url(master_playlist)
        async for chunk in self.stream_segments(segments_url):
            if chunk: yield chunk