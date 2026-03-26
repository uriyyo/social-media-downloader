from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from httpx import AsyncClient

from .schemas import AudioMedia, ImageMedia
from .utils import httpx_client


async def _download_file(
    client: AsyncClient,
    url: str,
    path: Path,
    *,
    headers: dict[str, str] | None = None,
) -> None:
    response = await client.get(url, headers=headers or {})
    response.raise_for_status()
    path.write_bytes(response.content)


async def images_to_video(
    images: list[ImageMedia],
    audio: AudioMedia,
    *,
    duration_per_image: float = 3.0,
    client: AsyncClient | None = None,
) -> bytes:
    async with httpx_client(client) as client:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)

            # Download all assets in parallel
            tasks = [
                _download_file(client, img.url, tmp_dir / f"img_{i:04d}.jpg", headers=img.headers)
                for i, img in enumerate(images)
            ]
            tasks.append(
                _download_file(client, audio.url, tmp_dir / "audio.mp3", headers=audio.headers),
            )
            await asyncio.gather(*tasks)

            # Build a concat demuxer file for ffmpeg
            concat_path = tmp_dir / "concat.txt"
            lines = []
            for i in range(len(images)):
                lines.append(f"file 'img_{i:04d}.jpg'")
                lines.append(f"duration {duration_per_image}")
            # Repeat last image to avoid ffmpeg cutting it short
            if images:
                lines.append(f"file 'img_{len(images) - 1:04d}.jpg'")
            concat_path.write_text("\n".join(lines))

            output_path = tmp_dir / "output.mp4"

            process = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_path),
                "-i",
                str(tmp_dir / "audio.mp3"),
                "-vf",
                "scale='if(gt(iw,1080),1080,iw)':'if(gt(ih,1920),1920,ih)':force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                "-movflags",
                "+faststart",
                str(output_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate()

            if process.returncode != 0:
                msg = f"ffmpeg failed with code {process.returncode}: {stderr.decode()}"
                raise RuntimeError(msg)

            return output_path.read_bytes()


__all__ = [
    "images_to_video",
]
