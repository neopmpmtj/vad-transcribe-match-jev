# Single-request classifier

This command asks Jev whether one entry is exactly one request. It prints `yes` or `no`, then a confidence score. It does not listen to the microphone, and the listener does not call it.

The question and the cutoff are in `src/jev/config.py`. Change a value, save, and run the command again.

## API key

The key for this module lives in `src/jev/.env`, beside the classifier. Open that file and set it:

```
TYPESAFE_API_KEY=...
```

The command reads that file on every run. The file is not committed.

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
- `Missing TypeSafe API key. Set TYPESAFE_API_KEY in src/jev/.env.` The key line is empty or the file is missing.
- `TypeSafe rejected the API key. Check TYPESAFE_API_KEY in src/jev/.env.` A key is present and TypeSafe refused it, or the key text itself is not usable.
- `Could not reach TypeSafe. Check the network, then run the command again.` The connection failed, or TypeSafe did not answer within a minute.
- `TypeSafe rate limit reached. Wait a moment, then run the command again.`
- `This API key is not allowed to call the model.`
- `The model was not found. The model name is jev-latest in src/jev/config.py.` The name in that sentence is the `model` value from the config.
- `TypeSafe rejected the request. Check the question in src/jev/config.py.`
- `TypeSafe had a server error. Run the command again.`
- `TypeSafe returned an answer that could not be read. Run the command again.`
- Another TypeSafe status prints `TypeSafe request failed` and the status code.
