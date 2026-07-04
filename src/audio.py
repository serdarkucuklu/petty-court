import subprocess

def build_command(wav, out_mp3, intro=None, outro=None):
    inputs, n = [], 0
    for f in [intro, wav, outro]:
        if f: inputs += ["-i", f]; n += 1
    if n > 1:
        streams = "".join(f"[{i}:a]" for i in range(n))
        fc = f"{streams}concat=n={n}:v=0:a=1[c];[c]loudnorm=I=-16:TP=-1.5:LRA=11[a]"
    else:
        fc = "[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[a]"
    return ["ffmpeg", "-y", *inputs, "-filter_complex", fc,
            "-map", "[a]", "-c:a", "libmp3lame", "-b:a", "128k", out_mp3]

def to_mp3(wav, out_mp3, intro=None, outro=None, runner=subprocess.run):
    runner(build_command(wav, out_mp3, intro, outro), check=True)
    return out_mp3
