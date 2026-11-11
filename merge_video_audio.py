"""
Combines the recorded PayResolve AI walkthrough video with a user voiceover audio file,
automatically matching the video playback speed to the audio length (keeping total length under 3:00).

Usage:
    .\venv\Scripts\python.exe merge_video_audio.py <path_to_audio_file>
"""

import subprocess
import sys
from pathlib import Path
import imageio_ffmpeg


def get_duration(ffmpeg_exe: str, media_path: str) -> float:
    p = subprocess.run([ffmpeg_exe, "-i", media_path], capture_output=True, text=True)
    for line in p.stderr.splitlines():
        if "Duration:" in line:
            parts = line.split("Duration:")[1].split(",")[0].strip().split(":")
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    raise RuntimeError(f"Could not determine duration of {media_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python merge_video_audio.py <path_to_audio_file>")
        sys.exit(1)

    audio_path = Path(sys.argv[1]).resolve()
    if not audio_path.exists():
        print(f"Error: Audio file not found: {audio_path}")
        sys.exit(1)

    video_path = Path("docs/video/PayResolve_AI_Demo_Walkthrough.mp4").resolve()
    output_path = Path("docs/video/PayResolve_AI_Final_YouTube_Submission.mp4").resolve()
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    vid_dur = get_duration(ffmpeg_exe, str(video_path))
    aud_dur = get_duration(ffmpeg_exe, str(audio_path))
    print(f"Video duration: {vid_dur:.2f}s | Audio duration: {aud_dur:.2f}s")

    # Adjust video PTS so the walkthrough finishes right with the voiceover (capped at 175s for Devpost 3-min rule)
    target_dur = min(aud_dur + 1.5, 175.0)
    pts_ratio = target_dur / vid_dur

    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-filter_complex", f"[0:v]setpts={pts_ratio:.4f}*PTS[v]",
        "-map", "[v]",
        "-map", "1:a",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_path),
    ]
    print("Merging video and audio into:", output_path)
    subprocess.run(cmd, check=True)
    final_dur = get_duration(ffmpeg_exe, str(output_path))
    print(f"SUCCESS! Final video ready at: {output_path} (Duration: {final_dur:.1f}s)")


if __name__ == "__main__":
    main()

