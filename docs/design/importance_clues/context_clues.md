# Context clues

Clues to an object's importance that depend on more than one moment or more than one source: the ongoing
topic, the genre, time, and the viewer. Part of the [importance clues](README.md). Discourse topic and genre
used to be in group G of [linguistic_clues.md](linguistic_clues.md).

## A. Time and what happened before

| Factor | Why it matters | How to get it |
|---|---|---|
| Newness | A newly appearing or newly mentioned object gets more attention than one seen for a long time | Track age |
| Discourse topic | The topic stays important between mentions | LLM keeps a running topic |
| Inhibition of return | Once looked at, a static object is less likely to be looked at again soon (Posner & Cohen 1984) | Decay with time on screen |
| Story / task relevance | The object needed for the next step (the knife before slicing) is looked at early (Land & Hayhoe 2001) | LLM with the transcript and the genre |
| How recently it was mentioned | An object named 2 s ago is still on the viewer's mind; one named 2 min ago is not | Time since the last mention |
| When importance ends | Importance from a mention has to stop: when the next object is named, at a shot cut, or when the object leaves the frame | Rule plus shot boundary detection |

## B. The video and the viewer (genre, task, screen)

| Factor | Why it matters | How to get it |
|---|---|---|
| Genre / purpose of the video | Sports: ball; cooking: hands and food; vlog: face | Classifier or LLM on title + first seconds |
| Viewer's own task or question | The same video is watched differently with different goals (Yarbus 1967) | Unknown at encode time; could come from a search query or a chapter title |
| Personal interests | Different viewers care about different things | Only with per-user streaming |
| Screen size and viewing distance | On a phone the sharp area of vision covers more of the frame, so the background degrades less visibly | Device type from the player |

Genre sets priors: in sports commentary the ball and players; in cooking food and hands; in a product review
the product; in a vlog the speaker's face; in a documentary the narrated subject; in film dialogue the
speaking character.

## References

- Land, Hayhoe (2001). In what ways do eye movements contribute to everyday activities? Vision Research.
- Posner, Cohen (1984). Components of visual orienting. Attention and Performance X.
- Yarbus (1967). Eye Movements and Vision. Plenum.
