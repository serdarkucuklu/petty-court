import subprocess


def build_command(mp3, cover, out_mp4):
    return ["ffmpeg", "-y", "-loop", "1", "-i", cover, "-i", mp3,
            "-filter_complex",
            "[1:a]showwaves=s=1280x200:mode=line:colors=white[wave];"
            "[0:v]scale=1280:720[bg];[bg][wave]overlay=0:520[v]",
            "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-shortest", out_mp4]


def to_mp4(mp3, cover, out_mp4, runner=subprocess.run):
    runner(build_command(mp3, cover, out_mp4), check=True)
    return out_mp4
