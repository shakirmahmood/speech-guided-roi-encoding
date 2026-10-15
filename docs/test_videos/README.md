# Choosing test videos

What makes a video a good test case for speech-guided ROI encoding. This is a working proposal (2026-10-15),
not a decision; it addresses the "Target content type" and "Test dataset" open questions in
[design.md](../design.md) §9.

| File | Purpose |
|---|---|
| README.md | Definition, research terms and a checklist for candidate clips |
| [video_types.csv](video_types.csv) | 446 video types with five fit facets and a rating |
| [video_types.md](video_types.md) | Column key for the CSV and the rating rule |

## Definition

A good test video is a **narrated** video whose speech is **visually grounded** and **temporally aligned**. Its
**referring expressions** pick out one **referent** among several **distractors** in a **cluttered** scene while
that referent is on screen. The referent is not the scene's most **salient** object, covers a small part of the
frame, and stays in view across long shots. The rest of the frame has high **spatial and temporal information
(SI/TI)**, so it is costly to encode.

Short version: the speech keeps naming one of several things in view, while it is in view, in shots long enough to
follow it.

This is narrower than "high audio-visual correlation", which usually means a sound matches its visible source (lips
in sync with speech, a dog barking on screen). A talking-head video has near-perfect audio-visual correlation, but
its speech names nothing on screen.

## Terms

| Term | Meaning here | Field |
|---|---|---|
| Visual grounding | The speech names things that are visible. Finding the named object in space and time is called spatio-temporal video grounding (Zhang et al. 2020). | Vision and language |
| Temporal alignment | The naming happens while the object is on screen. Narration in how-to videos often runs ahead of or behind the picture. | Vision and language |
| Referring expression | The phrase that names the object. Category nouns ("the red mug") work; deictic words ("this", "here") and proper names ("Messi") give a segmenter nothing to search for. | Linguistics |
| Referent, distractors | The named object, and the other objects competing with it. | Linguistics |
| Visual clutter | How busy the frame is ([Rosenholtz et al. 2007](https://doi.org/10.1167/7.2.17)). | Vision science |
| Bottom-up saliency | How eye-catching something is from the image alone. If the referent is already the most salient object, a visual saliency model finds it without speech, so the clip can't show what speech adds. Speech supplies top-down attention. | Vision science |
| Average shot length | Mean time between cuts. | Film studies |
| SI/TI | Spatial and temporal information (ITU-T P.910): how much detail and motion a video has, and so how costly it is to encode. | Video quality |
| Language-mediated eye movements | Listeners look at a named object within about 200 ms of hearing its name (Allopenna et al. 1998), studied with the visual world paradigm (Tanenhaus et al. 1995). This is the effect the method relies on: motivation, not a selection criterion. | Psycholinguistics |

## Video types and facets

[video_types.csv](video_types.csv) rates video types (cooking show, house tour, podcast, ...) on five facets. Each
facet is one part of the definition, judged for a typical video of the type:

| Facet | Part of the definition |
|---|---|
| Speech type | Narrated: one person describing the scene |
| Speech-to-picture link | Visually grounded, temporally aligned speech |
| Visual competition | Distractors, clutter |
| Shot scale | Referent is a small part of the frame |
| Editing pace | Long shots (average shot length) |

The values are typical-case estimates, not measurements. The key and the rating rule are in
[video_types.md](video_types.md).

## Checklist for a candidate clip

A video type only says what is likely. Each clip is checked on its own:

| Check | Why | How to measure |
|---|---|---|
| Speech names things on screen (grounding) | The method needs something to boost | Share of mentioned nouns that SAM 3 finds on screen when spoken |
| Naming happens while the object is visible (alignment) | A mention with nothing visible gives nothing to boost | Gap between the word's time and the object's appearance |
| Mentions are category nouns | A segmenter needs a category to search for | Count in the transcript |
| Several candidate objects | With one obvious subject, any method finds it | Objects detected per frame |
| Referent is not the most salient object | Otherwise visual saliency alone finds it | Referent's rank in a saliency map |
| Referent is a small part of the frame | Leaves background bits to move | Mask area as a share of the frame |
| Long shots, trackable referent | Time to find and follow the object; not hidden or motion-blurred | Average shot length (PySceneDetect); track length |
| Clear audio: one main speaker, little music or noise | Speech-to-text accuracy | Speech share, speaker count (diarization) |
| Viewers understand the language | Speech can't steer the eyes of people who don't follow it | Language of the viewing-test participants |
| No talking face or burned-in captions | A visible talking face draws gaze ([Foulsham & Sanderson 2013](https://repository.essex.ac.uk/9321/)); viewers spend 40 to 60% of subtitle display time reading ([Szarkowska & Gerber-Morón 2018](https://doi.org/10.1371/journal.pone.0199331)) | Look at the clip |
| Costly background | If plain encoding already looks fine, moving bits shows little | SI/TI (ITU-T P.910) |
| High-bitrate source | Re-encoding a compressed copy mixes its old artifacts into the results | Source codec and bitrate |
| Stable, usable licence | Clips must be shown to viewers, published and kept | Licence; record it in [clips.csv](../../data/manifests/clips.csv) |
| Ground truth available | Lets each step be checked | Transcripts, object boxes, eye-tracking |

## References

- Allopenna, Magnuson & Tanenhaus (1998). Tracking the time course of spoken word recognition using eye movements.
  *Journal of Memory and Language* 38(4).
- Foulsham & Sanderson (2013). Look who's talking? Sound changes gaze behaviour in a dynamic social scene. *Visual
  Cognition* 21(7).
- ITU-T P.910. Subjective video quality assessment methods for multimedia applications (defines SI and TI).
- Rosenholtz, Li & Nakano (2007). Measuring visual clutter. *Journal of Vision* 7(2):17.
- Szarkowska & Gerber-Morón (2018). Viewers can keep up with fast subtitles: Evidence from eye movements. *PLOS ONE*
  13(6).
- Tanenhaus, Spivey-Knowlton, Eberhard & Sedivy (1995). Integration of visual and linguistic information in spoken
  language comprehension. *Science* 268.
- Zhang et al. (2020). Where does it exist: Spatio-temporal video grounding for multi-form sentences. *CVPR*.
