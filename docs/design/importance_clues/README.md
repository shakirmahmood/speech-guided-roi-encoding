# Importance clues

Everything that can tell us how important an object on screen is, in one place. The speech is our main
signal, but it is not the only thing that decides where viewers look. Draft, like the rest of the design.

| File | Clues from | Produced by |
|---|---|---|
| [linguistic_clues.md](linguistic_clues.md) | The words and how they are said: reference, visibility, salience, place, timing, actions, prosody | The LLM reading the transcript and frames; audio for prosody |
| [visual_clues.md](visual_clues.md) | The picture: visual saliency, object category, what people on screen do, filming and editing | Vision models (saliency, face, text, hand, gaze, shot detection) |
| [sound_clues.md](sound_clues.md) | Sounds other than speech | Sound event detection and sound source localization |
| [context_clues.md](context_clues.md) | Time, the ongoing topic, the genre, the viewer | The LLM over the whole video; track history; the player |

A clue that depends on more than one source (genre, the ongoing topic) is listed once, in
`context_clues.md`. How many bits an important object needs is a different question and is in
[roi_encoding.md](../roi_encoding.md) ("Where compression damage shows").

## What the clues decide

The clues do three different jobs:

1. **Whether** an object gets any importance from a mention. A past, future, hypothetical, generic, negated
   or off-screen mention gives none (linguistic group B). The frames have the last word: if the object
   isn't visible, it gets nothing.
2. **How much** importance it gets (linguistic groups C, F, H; visual; sound).
3. **When and for how long** (linguistic group E; context group A).

## Open: how the clues combine

Nothing yet says how the clues add up to one importance value per object per frame. This is the main open
question of the method (see also [_design.md](../_design.md) §5.5).

## Plain-language guide

A standalone guide to the language clues, with examples from many kinds of video:
[speech_clues_explained.md](speech_clues_explained.md).

## Checking the clues

How to test the step that picks the important objects against these clues: [testing.md](testing.md).

Eye-tracking recordings show what people actually looked at, so they are the ground truth for all clues
here. Datasets with eye tracking: DIEM, Coutrot1/2, AVAD, LEDOV, DHF1K (Coutrot2 and DIEM have speech).
Attentional synchrony, meaning many viewers looking at the same place at once, shows when a region clearly
matters; when gaze is spread out, a uniform encode is safer.
