# User guide

This guide gets `python -m vad` running and explains the voice-activity settings you can change. The program listens on the default microphone, sends each finished phrase to OpenAI, and prints the transcript. A listed phrase in that transcript is printed underneath.

You need Python 3.12 or newer, a working microphone, and an OpenAI API key. The key stays in `src/transcribe/.env` on this machine. Do not commit it.

## Install

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Activate the same virtualenv in later terminals before you run the listener. The prompt shows `(.venv)` when it is active.

## API key and language

Open `src/transcribe/.env` and set the key:

```
OPENAI_API_KEY=sk-...
```

The language hint is `language` in `src/transcribe/config.py`. It is `en`. Leave it as `""` to let the model choose the language. To force one, set a code:

| Code | Language |
| --- | --- |
| `en` | English |
| `pt` | Portuguese |
| `es` | Spanish |
| `fr` | French |
| `nl` | Dutch |
| `de` | German |
| `no` | Norwegian |
| `it` | Italian |

## Run it

Stay in the repository root, with the virtualenv active:

```bash
python -m vad
```

Stay quiet for a moment. The first line after the room measurement looks like this:

```
Ready. Room level 0.0002.
```

Speak a phrase, then stop. After about 2 seconds of silence the terminal prints:

```
[1] voice started
[1] silence
[1] Okay, go.
okay go
```

`voice started` means the listener accepted speech. `silence` means the 2 second pause ended the phrase. The next line is the transcript. If a configured phrase is in that transcript, it is printed on its own line. Two or more matches are printed as a list:

```
['okay go', 'Pamela off,']
```

The microphone is not read while OpenAI is answering, so the next phrase starts after the transcript appears. Ctrl+C stops the program. A phrase that has not reached silence is not sent.

## Phrases to watch for

Edit `src/phrase_match/config.py`. The list that ships with the repo is:

```python
enabled: bool = True
phrases: tuple[str, ...] = ("okay go", "Pamela off,")
```

A single phrase still needs a comma inside the parentheses. Without it, Python treats the line as plain text and the match will not work:

```python
phrases: tuple[str, ...] = ("okay go",)
```

More than one phrase uses a comma between items, and the last item still has a comma if you want to keep the habit:

```python
phrases: tuple[str, ...] = ("okay go", "lights")
```

Matching ignores capital letters, accents, and punctuation. The words have to sit next to each other.

- `Okay, go.` matches `okay go`.
- `Okay, here we go.` does not, because `here` is between the two words.
- `cat` does not match `category`.

Set `enabled = False` to stop phrase printing. The transcript is still printed.

## When something fails

Each of these is printed on its own, and the listener waits for the next phrase.

- `Missing OpenAI API key. Set OPENAI_API_KEY in src/transcribe/.env. The next phrase reads that file again.` The key line is empty or the file is missing. Save the file. The next phrase reads it again.
- `OpenAI rejected the API key. Check OPENAI_API_KEY in src/transcribe/.env. The next phrase reads that file again.` A key is present and OpenAI refused it. Replace the value. The next phrase reads the file again.
- `OpenAI refused the request because the account has no quota or no funds. Fix billing, then speak again.`
- `Could not reach OpenAI. Check the network, then speak again.` The connection failed, or OpenAI did not answer within a minute.
- A rate limit, a server error, a key that cannot use the model, or another OpenAI status prints one short sentence of the same kind. The listener then waits for the next phrase.
- A phrase you can see in the transcript is not printed underneath. Check the trailing comma, and check that the words are next to each other in the transcript.
- `Room level` stays near `0.0001` or `0.0002`. The operating-system input volume is low. Raise the default microphone volume before changing listener settings. On this machine the built-in digital microphone has been seen at about one third volume.
- After `silence`, the program is sending the phrase to OpenAI. A wait longer than a minute prints the network sentence above. The next `voice started` comes after the transcript line or that failure sentence.

## Voice activity and settings

After a run works, the knobs that decide when a phrase starts and ends are in `src/vad/settings.py`. Each value below is the one the file uses now. Change the number, save, and run `python -m vad` again.

A frame is 40 ms of audio. The listener steps that window forward every 20 ms.

### Timing

`sample_rate` is `16000`. This is how many samples per second are read from the microphone. Leave it at 16000. The transcriber receives audio at this rate. Raising it asks the sound card for a different rate and changes every time calculation below.

`frame_s` is `0.04`. Each voice decision looks at the last 40 ms. A longer frame is steadier and slower to react. A shorter frame reacts faster and is easier to fool with a short noise.

`hop_s` is `0.02`. The window moves forward 20 ms each step. This is also the size of each piece stored in the capture. A smaller hop checks more often. A larger hop checks less often and makes `consecutive` cover more clock time.

`calibration_s` is `0.5`. This is the quiet wait at the start. The median loudness of that wait is printed as `Room level`. A longer calibration is a steadier room measurement. A shorter one finishes sooner and is more likely to catch a sound that was already happening.

`silence_s` is `2.0`. This is the pause that ends the phrase and sends it to OpenAI. Raise it if the listener cuts you off while you are still talking. Lower it if you wait too long after you stop. This is not the same control as `release_consecutive`.

### Starting and stopping

These three are read by `src/vad/onset.py`.

`consecutive` is `5`. Speech must be accepted on 5 steps in a row before the terminal prints `voice started`. At the current hop, that is about 0.1 seconds once the voice check is already saying yes. Raise it if noise is opening phrases. Lower it if the start of real speech is detected late. If the words are present but the recording starts late, prefer `preroll_s` below before lowering this.

`gap_frames` is `1`. While those 5 voiced steps are building up, one quiet step is allowed without throwing the count away. Raise it to forgive more brief dropouts before the phrase has started. Lower it to `0` to require an unbroken run.

`release_consecutive` is `6`. After a phrase has started, the gate stays shut until 6 quiet steps in a row. Then it can arm for another phrase. Raise it if a short gap in one sentence lets a second phrase start too soon. Lower it if the next sentence is ignored because the gate is still shut. The recording still ends when `silence_s` is reached. This count only decides when a new `voice started` is allowed.

### Loudness

`noise_multiplier` is `3.0`. The level floor is this many times the measured room level. Raise it if the room itself is being treated as speech. Lower it if quiet speech never crosses the floor. Do this after the operating-system microphone volume is already reasonable.

`min_level` is `0.0001`. The floor is never lower than this, even when the room measures quieter. A printed room level of `0.0001` or `0.0002` means the microphone stream is sitting on that floor. Raising `min_level` demands a louder signal. Lowering it lets a very quiet stream through, including noise. Check the microphone volume before lowering it.

The floor used for the rest of the run is the larger of `noise_multiplier` times the room level, and `min_level`.

### Speech shape

These live in the same settings file and are applied in `src/vad/voice.py`. Loudness is only the first test. A clap is loud and has no pitch. A beep is one tone. Speech in this band has a pitch and a stack of overtones. Leave this group alone unless real speech is refused or noise is accepted.

`min_harmonicity` is `0.35`. This is how strong the pitch has to be, from 0 to 1. Raise it to reject more noisy sounds. Lower it if a quiet or breathy voice never counts as voiced.

`pitch_low_hz` is `70` and `pitch_high_hz` is `400`. The pitch search only looks inside this range. Widen it if a very low or very high voice is missed. Narrow it if pitches outside normal speech are being accepted.

`min_f0_hz` is `75` and `max_f0_hz` is `360`. A pitch that was found, but sits outside this range, is not speech. These are slightly inside the search range. Raise `min_f0_hz` or lower `max_f0_hz` to be stricter. Move them toward the search limits to be looser.

`min_fund_share` is `0.12` and `max_fund_share` is `0.95`. Of the energy on the first three partials, this is how much may sit on the fundamental. A vowel sits between the two numbers. A pure beep sits near the top, so `max_fund_share` rejects it. Raise `min_fund_share` or lower `max_fund_share` to be stricter. Widen the gap to accept more sounds.

`max_peak_ratio` is `0.5`. If one frequency bin holds more than half of the spectrum, the frame is rejected. Lower it to reject narrow tones more aggressively. Raise it to allow a stronger single peak.

`harmonic_band_hz` is `45`. This is the width, in hertz, around each partial when the fundamental share is measured. Widen it if the pitch estimate is a little off and real vowels are rejected. Narrow it if nearby noise is being counted as a partial.

## If this happens, change this

Speech is missing from the start of the transcript. Raise `preroll_s` in `src/record/config.py`. It is `1.5` seconds. Lower `consecutive` only when `voice started` itself is late.

The phrase is cut off while you are still talking. Raise `silence_s`.

The listener waits too long after you stop. Lower `silence_s`.

Noise starts a phrase. Raise `consecutive`, `min_harmonicity`, or `noise_multiplier`.

Quiet speech never starts. Lower `consecutive` or `min_harmonicity`, and check the operating-system microphone volume before lowering `min_level`.

The transcript is faint or poor even though the phrase was detected. `gain` and `target_peak` in `src/record/config.py` scale the audio before it is sent. They are `1.0` and `0.45`. They do not change when a phrase starts. `target_peak` above zero rescales each utterance so its loudest sample lands on that level.
