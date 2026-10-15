# Video types: column key

Key for [video_types.csv](video_types.csv): 446 video types. Each row describes a typical video of that type. How
the facets relate to a good test video is in the [README](README.md).

## Columns

| Column | Meaning |
|---|---|
| Video type | Name of the type. |
| Short description | One-line description. |
| Best for our project | Rating from the five facets: Best, Good, Fine or Bad, or Depends where the type doesn't fix the content (rule below). |
| Group | The family the type belongs to (19 groups, e.g. Film, News, Online creator formats). |
| Speech type | The main kind of speech in a typical video of this type. |
| Speech-to-picture link | How often the speech names what is on screen at that moment. |
| Visual competition | How many things compete for the viewer's attention in a typical frame. |
| Shot scale | The dominant framing. |
| Editing pace | How often the shot changes. |

The last five columns are the fit facets. They decide whether speech can steer the encoder: speech must exist and
name visible things, there must be more than one thing it could pick, the named object should be a small part of the
frame, and shots must last long enough to find and track it.

## Values

**Speech type**
- Dialogue: characters or people talking to each other in scripted scenes.
- Conversation: real people talking with each other (interviews, podcasts, calls).
- Talking to camera: an on-screen presenter speaks to the viewer.
- Voice-over narration: an unseen narrator speaks over the footage.
- Live commentary: a commentator describes events as they happen (sports, games, live coverage).
- Speech to audience: a talk, lecture, sermon or address to a room.
- Singing: sung vocals carry the words.
- Sign language: content is signed.
- Music only, Ambient sound only, No audio: no meaningful speech.
- Mixed: several of the above in one video.
- Depends: the type does not determine it (mostly medium or format rows such as "3D CGI animation" or "HDR video").

**Speech-to-picture link**
- High: most sentences name or describe something visible right then (demos, tutorials, tours, live commentary).
- Medium: some of the time.
- Low: rarely; the speech is mostly about things not shown (podcasts, anchors, most film dialogue).
- None: no speech.
- Depends: see above.

**Visual competition**
- High: many plausible things to look at (cluttered scenes, crowds, busy screens).
- Medium: a few.
- Low: one obvious subject (a face, a single product, a single performer).

**Shot scale**
- Close-up, Medium, Wide, Mixed (no dominant scale), Screen/graphics (screen capture, slides or graphics rather than
  camera footage).

**Editing pace** (rough average shot length)
- Continuous: one unedited take or a live feed.
- Slow: about 8 s or more per shot.
- Medium: about 3 to 8 s.
- Fast: under about 3 s, or rapid jump cuts.

## How the values were set

They are typical-case estimates for each type made by Claude (AI assistant) on 2026-10-15, not measurements.
Individual videos vary, so treat them as a starting point to correct. Each facet can be measured on a real clip:

| Facet | Measure |
|---|---|
| Speech type | Speech share and speaker turns from the transcript (WhisperX) |
| Speech-to-picture link | Share of mentioned nouns that SAM 3 finds on screen at the time they are spoken |
| Visual competition | Objects or people detected per frame |
| Shot scale | Area of the named object's mask as a share of the frame |
| Editing pace | Average shot length from PySceneDetect |

## Ideal values

Each facet is a separate condition, so a video should meet all of them rather than add up a score.

| Facet | Ideal value | Why |
|---|---|---|
| Speech type | One person describing the scene: talking to camera, voice-over narration or live commentary | A single describer names what to look at |
| Speech-to-picture link | High | The speech has to keep naming visible things |
| Visual competition | High | With one obvious subject, any method finds it; speech matters when it has to pick |
| Shot scale | Wide or Mixed | The named object should be a small part of the frame so there are bits to move |
| Editing pace | Slow or Continuous | Shots need to last long enough to find and follow the object |

## Rating rule for "Best for our project"

Each facet counts the steps between its value and the ideal:

- Speech type: talking to camera, voice-over narration, live commentary or Mixed = 0; anything else = 1.
- Speech-to-picture link: High = 0, Medium = 1. Low or None makes the type Bad outright, because the speech doesn't
  point at anything on screen.
- Visual competition: High = 0, Medium = 1, Low = 2.
- Shot scale: Wide or Mixed = 0, Medium = 1, Close-up = 2, Screen/graphics = 2 (screen recordings aren't camera
  footage, and blurring background text hurts readability).
- Editing pace: Slow or Continuous = 0, Medium = 1, Fast = 2.

Total steps: 0 = **Best** (9 types), 1 = **Good** (21), 2 to 3 = **Fine** (87), 4 or more = **Bad** (311). Format or
medium rows whose content isn't fixed (animation styles, 360-degree, HDR and similar) are marked **Depends** (18).

- **Best:** cooking show, gardening video, room / house / apartment tour, real estate property tour, virtual field
  trip / tour, urban exploration, wildlife safari video, sports tactical breakdown, breaking news live coverage.
- **Suggested first test set:** one clip from each of five Best types that look different from each other (house
  tour, safari video, cooking show, urban exploration, sports tactical breakdown), plus one or two Bad types (e.g. a
  video podcast, a music video) as controls to show where the method stops helping.

Two caveats: sports commentary names players more often than object categories, and screen recordings are not camera
footage.

## Sources for the type list

YouTube's video category list; Wikipedia's "List of genres" and "List of television formats and genres"; Bill
Nichols' six documentary modes; Twitch stream categories; marketing, e-learning and creator-format guides (Adobe, B2W,
Soundstripe, Castmagic, EdTech Turkiye, Foxi Music); the YouTube UGC dataset categories; and an edge video analytics
survey (arXiv 2211.15751) for camera and sensor sources.
