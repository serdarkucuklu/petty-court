import wave

def render_text(script):
    return "\n".join(f"{l.speaker}: {l.text}" for l in script.lines)

def pcm_to_wav(pcm_bytes, path, rate=24000):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)          # 16-bit
        w.setframerate(rate)
        w.writeframes(pcm_bytes)
    return path

def synthesize(script, cfg, tts_fn, out_path):
    pcm = tts_fn(render_text(script))
    return pcm_to_wav(pcm, out_path)

def gemini_tts_fn(api_key, hosts):
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key)
    speakers = [
        types.SpeakerVoiceConfig(
            speaker=name,
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)))
        for name, voice_name in hosts.items()
    ]
    def _fn(text):
        resp = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts", contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                        speaker_voice_configs=speakers))))
        return resp.candidates[0].content.parts[0].inline_data.data
    return _fn
