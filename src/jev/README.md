# Single-request classifier

This command asks Jev whether one entry is exactly one request. It prints `yes` or `no`, then a confidence score. It does not listen to the microphone, and the listener does not call it.

The question and the cutoff are in `src/jev/config.py`. Change a value, save, and run the command again.

## API key and address

Both live in `src/jev/.env`, beside the classifier. The command reads that file on every run. The file is not committed.

```
TYPESAFE_API_KEY=...
JEV_API_URL=https://api.typesafe.ai/v1/systemone
```

`JEV_API_URL` is the systemone address. The client keeps the host in front of `/v1/systemone` and posts to that path. Every question type goes to this one address. Listing model names is a separate path, `GET /v1/models`, on the same host.

## Run it

From the repository root, with the virtualenv active:

```bash
python -m jev What is the time?
```

Words after the command are the entry. With no words, the command reads stdin until it ends. Type a paragraph and press Ctrl-D, or pipe a file:

```bash
python -m jev < note.txt
```

A blank entry is not sent.

## What you see

```
yes
confidence 0.92
```

`yes` means the probability was at least `yes_at`. That cutoff is `0.5`. `no` means the probability was under the cutoff.

The score runs from `0.00` to `1.00`. It is how far the probability of yes sits from an even split. `1.00` means that probability was `0` or `1`. `0.00` means it was `0.50`. With the cutoff at `0.5`, a `yes` and a high score is a clear single request, and a `no` and a high score is a clear rejection. A score near `0.00` is a close call. The word is still `yes` or `no`.

## The question

Jev is asked one yes-or-no question: is this entry exactly one request? The state it sees is the entry text. The two sides are `true_case` and `false_case`.

On the yes side, the whole entry asks for one thing. A standalone question counts. Polite wording, such as "could you", still counts. A span of time still counts as one thing. These are each one request:

- What is the time?
- What does the weather look like in my area?
- Check the weather for the next three days.
- Make a calendar entry.

On the no side:

- A journal paragraph. A question inside that paragraph does not turn the paragraph into one request.
- An observation.
- An exclamation.
- A greeting that asks for nothing.
- Two requests together, such as asking the time and also asking for a calendar entry.

`model` in the same file is `jev-latest`.

## When something fails

Each of these is printed on its own, and the command exits. A failure is not printed as `no`.

- `Enter the text to classify.` The entry was blank.
- `Missing TypeSafe API key. Set TYPESAFE_API_KEY in src/jev/.env. The next run reads that file again.` The key line is empty or the file is missing.
- `Missing TypeSafe API URL. Set JEV_API_URL in src/jev/.env. The next run reads that file again.` The address line is empty.
- `JEV_API_URL in src/jev/.env must be the systemone address, ending in /v1/systemone.`
- `TypeSafe rejected the API key. Check TYPESAFE_API_KEY in src/jev/.env. The next run reads that file again.` A key is present and TypeSafe refused it, or the key text itself is not usable.
- `Could not reach TypeSafe. Check the network, then run the command again.` The connection failed, or TypeSafe did not answer within a minute.
- `TypeSafe rate limit reached. Wait a moment, then run the command again.`
- `TypeSafe refused the request because the account has no quota or no funds. Fix billing, then run the command again.` The response body carried a billing code.
- `This API key is not allowed to call the model.`
- `The model was not found. The model name is jev-latest in src/jev/config.py.` The name in that sentence is the `model` value from the config.
- `TypeSafe had a server error. Run the command again.`
- `TypeSafe is overloaded. Wait a moment, then run the command again.` TypeSafe answered `529`.
- Another TypeSafe status prints `TypeSafe request failed` and the status code.

## Revise the cases

`python -m jev.feedback_enhance` sends a report to OpenAI and prints a note, a true case, and a false case. The report is a complaint, an example, a suggestion, or a correction. It does not listen to the microphone, and the listener does not call it.

From the repository root, with the virtualenv active:

```bash
python -m jev.feedback_enhance Checking the weather for a whole week is still one request.
```

Words after the command are the report. With no words, the command reads stdin until it ends. A blank report is not sent.

The screen shows the note, then the true case, then the false case:

```
A week of weather is still one request, so that stays on the yes side.

true case
The whole entry asks for one thing.

false case
The entry is a journal paragraph.

y applies, n cancels, and revise asks a question.
```

`y` or `yes` writes a paragraph only when its words changed. The other paragraph stays as it is in `src/jev/config.py`, including its line breaks. `n` or `no` writes nothing. `revise` prints one question from the model. The next line is the answer, and a new note and two paragraphs are shown. `y` or `yes` at that question writes the proposal already on screen. `n` or `no` writes nothing.

The question, the model name, and the cutoff in `src/jev/config.py` stay as they are. The next `python -m jev` reads the cases from that file.

This command reads `OPENAI_API_KEY` from `src/jev/.env` on every run. The endpoint and the model are in `src/jev/feedback_enhance/config.py`. The model is `gpt-4.1-mini`.

The two paragraphs together have a character cap. The developer sets that cap as `max_cases_chars` in `src/jev/feedback_enhance/config.py`. The command does not ask for a new cap. A reply that is over the cap is shortened before it is shown.

## When a revision fails

Each of these is printed on its own. The cases file is not changed.

- `Enter the report.` The report was blank.
- `Run this command in a terminal to approve a change.` The command could not read an answer from the terminal.
- `Missing OpenAI API key. Set OPENAI_API_KEY in src/jev/.env. The next run reads that file again.` The key line is empty or the file is missing.
- `OpenAI rejected the API key. Check OPENAI_API_KEY in src/jev/.env. The next run reads that file again.` A key is present and OpenAI refused it.
- `Could not reach OpenAI. Check the network, then run the command again.` The connection failed, or OpenAI did not answer within a minute.
- `OpenAI rate limit reached. Wait a moment, then run the command again.`
- `OpenAI refused the request because the account has no quota or no funds. Fix billing, then run the command again.` The response body carried a billing code.
- `This API key is not allowed to call the model.`
- `The model was not found. The model name is gpt-4.1-mini in src/jev/feedback_enhance/config.py.` The name in that sentence is the `model` value from that config.
- `OpenAI had a server error. Run the command again.`
- Another OpenAI status prints `OpenAI request failed` and the status code.
- `The reply could not be read. Run the command again.`
- `The proposed cases are too long. Left src/jev/config.py unchanged.`
- `Could not update src/jev/config.py. Left that file unchanged.`

A failure while revising leaves the proposal already on screen in place. The command shows it again. `y` still writes that proposal. `n` still writes nothing.

When a paragraph is written, the command prints one of these:

- `Updated true case in src/jev/config.py.`
- `Updated false case in src/jev/config.py.`
- `Updated true case and false case in src/jev/config.py.`

When you cancel, or the words already match the file, it prints `Left src/jev/config.py unchanged.`
