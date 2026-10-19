# Sound clues

Clues to an object's importance that come from sounds other than speech. Part of the
[importance clues](README.md). How these are detected and located is in [_design.md](../_design.md) §5.4.

## Non-speech sound

| Factor | Why it matters | How to get it |
|---|---|---|
| Sound events (crash, bark, engine) | Sudden sounds pull gaze to their source | Sound event detection (PANNs, BEATs) + **sound source localization** |
| Audio-visual saliency | Sound changes where people look in video (Coutrot & Guyader 2014) | DAVE, STAViS, DiffSal |
| Music changes | Beat, rise in loudness marks a moment, rarely a single object | Audio features |

## References

- Coutrot, Guyader (2014). How saliency, faces, and sound influence gaze in dynamic social scenes. Journal of Vision.
