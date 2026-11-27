"""Open the microphone and transcribe each phrase after silence."""

import numpy as np

from phrase_match import found
from record import Recorder
from transcribe import transcribe

from .onset import OnsetDetector
from .settings import Settings
from .voice import frame_rms, is_voiced


def mic_frames(sample_rate: int, hop: int):
    import sounddevice as sd

    print("Listening on the default microphone. Ctrl+C to stop.")
    print("Stay quiet for a moment while the room noise is measured.")
    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
        blocksize=hop,
    ) as stream:
        while True:
            data = stream.read(hop)[0]
            yield np.asarray(data, dtype=np.float32).reshape(-1)


def main(settings: Settings) -> None:
    hop = int(settings.sample_rate * settings.hop_s)
    frame_n = int(settings.sample_rate * settings.frame_s)
    calibrate_frames = int(round(settings.calibration_s / settings.hop_s))
    buffer = np.zeros(frame_n, dtype=np.float32)
    filled = 0
    levels: list[float] = []
    detector = OnsetDetector(
        settings.consecutive,
        settings.release_consecutive,
        settings.gap_frames,
    )
    recorder = Recorder(settings.sample_rate)
    ready = False
    count = 0
    listening_for_voice = True
    silence_s = 0.0
    try:
        for block in mic_frames(settings.sample_rate, hop):
            buffer = np.roll(buffer, -hop)
            buffer[-hop:] = block
            filled += hop
            if filled < frame_n:
                continue
            level = frame_rms(buffer)
            if not ready:
                levels.append(level)
                if len(levels) < calibrate_frames:
                    continue
                noise = float(np.median(levels))
                level_floor = max(noise * settings.noise_multiplier, settings.min_level)
                ready = True
                print(f"Ready. Room level {noise:.4f}.")
                continue
            recorder.write(block)
            voiced = is_voiced(buffer, settings.sample_rate, level_floor, settings)
            if listening_for_voice:
                if detector.update(voiced):
                    count += 1
                    print(f"[{count}] voice started")
                    recorder.start()
                    listening_for_voice = False
                    silence_s = 0.0
                continue
            if voiced:
                silence_s = 0.0
                continue
            silence_s += settings.hop_s
            if silence_s < settings.silence_s:
                continue
            print(f"[{count}] silence")
            _transcribe(recorder, settings.sample_rate, count)
            listening_for_voice = True
            silence_s = 0.0
            detector.reset()
    except KeyboardInterrupt:
        print("\nStopping...")


def _transcribe(recorder: Recorder, sample_rate: int, count: int) -> None:
    audio = recorder.finish()
    if audio is None:
        return
    try:
        text = transcribe(audio, sample_rate)
    except Exception as exc:
        print(exc)
        return
    print(f"[{count}] {text}")
    _print_matches(found(text))


def _print_matches(matches: list[str]) -> None:
    if len(matches) == 1:
        print(matches[0])
        return
    if len(matches) > 1:
        print(matches)


if __name__ == "__main__":
    main(Settings())
