# Short-clip gate

This folder is the control for short false positives. After the listener prints `silence`, it measures how long the sound lasted and can skip the OpenAI call. A short bang is the case this covers. The check waits out the normal pause first. It runs in the moment before the audio would be sent.

The switches are in `src/short_clip_gate/config.py`. Change a value, save, and run `python -m vad` again.

```python
gate_enabled: bool = True
log_enabled: bool = True
min_content_s: float = 1.0
```

`gate_enabled` is the check itself. `log_enabled` is the database. Turning the database off leaves the check running.

## What you see

`voice started` and `silence` stay as they are. The next line depends on the clip.

A clip under the cutoff is not sent. Phrase matching is skipped, and the listener listens again:

```
[1] voice started
[1] silence
[1] No text detected
```

A clip that was sent, and came back blank or only whitespace, prints a different line. That call still spends the API request. Phrase matching is skipped:

```
[2] voice started
[2] silence
[2] Empty transcript
```

A clip with text prints the transcript, then any listed phrase, as before:

```
[3] voice started
[3] silence
[3] Okay, go.
okay go
```

An API error still prints the error and returns to listening. That clip adds no database row.

## The cutoff

`min_content_s` is `1.0`. The listener drops a clip only when the measured sound is strictly under this. A clip of exactly 1.0 seconds is sent.

The measured sound is the audio written after `voice started`, minus the quiet tail that just ended the phrase. With the current listener settings that tail is 2.0 seconds, and the capture also keeps 1.5 seconds from before `voice started`. Both of those are inside the audio that would be sent. Neither of them is part of this number. A bang that ends as soon as it is detected measures about 0 seconds. A sentence measures about how long the speech continued after the trigger.

The first tenth of a second, the part that armed the detector, sits in that lead-in. The measured number is a little shorter than the full spoken length.

If a real sentence is dropped, lower `min_content_s`. If bangs are still sent, raise it.

Short commands said on their own can fall under 1.0 seconds. The cutoff is the control for that. Raise or lower it after you hear what the listener keeps.

## Turning the check off

Set `gate_enabled` to `False` to restore the listener from before this check. Every finished clip is sent, a blank transcript is printed as an empty result line, and nothing is written to the database. Turning it off on purpose prints no warning.

If the `short_clip_gate` package cannot be loaded, the listener prints one `WARNING` on the error stream and sends every clip the same way. One bad length does the same for that clip: `None`, a value that is not a number, or a negative length is sent.

A database that cannot be opened prints one `WARNING` and skips writing for the rest of the run. The check keeps running. The first failed write in a run prints one `WARNING` and leaves the decision already made. The screen line stays, and a short clip stays unsent.

## The log

Set `log_enabled` to `False` when the cutoff is settled. The listener then does not load SQLite, does not open a database, and does not build a row. The check and the screen lines keep working.

While both switches are on, each finished clip adds one row: time, utterance number, measured seconds, full captured seconds, the cutoff used for that decision, and a reason of `short`, `empty`, or `sent`. The row has no transcript text and no audio. The file is `src/short_clip_gate/short_clip_gate.sqlite`, next to this manual. The path follows the module file, so the working directory does not matter. The file is listed in `.gitignore`.

While the check is off, rows are not written even if `log_enabled` is `True`.

Read the log with the virtualenv active, from the repository root:

```bash
python -m short_clip_gate
```

The command prints totals for the whole table, then the latest 20 rows. `fails` is `short` plus `empty`.

```
clips 48
sent 30 (62.5%)
short 15 (31.3%)
empty 3 (6.3%)
fails 18 (37.5%)
```

With `log_enabled` set to `False`, or with no database file yet, the command prints `No log.` and exits. The listener does not run this command.

## If this happens, change this

A real sentence is printed as `No text detected`. Lower `min_content_s`.

A bang is still sent to OpenAI. Raise `min_content_s`.

The cutoff is settled and the database work is no longer useful. Set `log_enabled` to `False`.

You want every finished clip sent, as before this check. Set `gate_enabled` to `False`.
