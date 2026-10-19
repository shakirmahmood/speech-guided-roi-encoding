# Visual clues

Clues to an object's importance that come from the picture. Part of the [importance clues](README.md).
Several of these are also the fallback when the speech points at something without naming it ("Look!"), and
the tie-breaker when a phrase could mean more than one object ("the dog" with two dogs).

## A. What the picture itself shows (visual saliency)

Things that grab the eye regardless of meaning (Itti, Koch & Niebur 1998).

| Factor | Why it matters | How to get it |
|---|---|---|
| Contrast in colour, brightness, orientation | Odd-one-out regions pop out | Classic saliency maps; learned video saliency models (TMFI-Net, ViNet, UNISAL) |
| **Motion** | In video, motion is the strongest single predictor of gaze; a moving object beats a still one (Mital et al. 2011, DIEM data) | Optical flow (RAFT), or motion vectors the encoder already computes |
| Sudden onset (something appears) | New objects capture attention automatically (Yantis & Jonides 1984) | Track birth in SAM 3 tracking; scene-change detection |
| Object size | Bigger objects get more looks, but small ones the speech names matter more per pixel | Mask area |
| Position (centre bias) | Viewers look at the frame centre far more than the edges (Tatler 2007) | Fixed centre-weighted prior |

## B. What kind of object it is (object category)

| Factor | Why it matters | How to get it |
|---|---|---|
| **Faces**, especially eyes and mouth | People look at faces almost always, even when nothing is said (Cerf et al. 2008) | Face detector |
| People and animals | Living things attract gaze over objects | SAM 3 / detector class |
| Text in the scene (signs, labels, captions) | Text is looked at and read automatically (Cerf et al. 2008) | Scene-text detection (OCR) |
| Hands and the objects in them | In task videos (cooking, repair) people look at hands and what is being handled (Land & Hayhoe 2001; Li et al. 2013, egocentric gaze) | Hand detector + hand-object contact |

## C. What the people on screen do (social cues)

| Factor | Why it matters | How to get it |
|---|---|---|
| **Gaze following** | Viewers look where an on-screen person looks (Frischen et al. 2007, gaze cueing) | Gaze-target estimation models (e.g. Gaze-LLE) |
| Speaker looks before naming | An on-screen speaker looks at an object about 1 s before naming it (Griffin & Bock 2000), so their gaze can mark the object early | Gaze-target estimation on the speaker |
| Pointing and showing | A pointed-at or held-up object is the referent of "this", "that" | Pose estimation + hand direction; the frames-aware LLM |
| **Active speaker** | Viewers look at whoever is talking, then at what they talk about (Coutrot & Guyader 2014) | Active speaker detection (AVA-ActiveSpeaker models such as TalkNet, LoCoNet) |

## D. How the video was filmed and edited (cinematography)

The filmmaker has already chosen what matters; viewers' gaze is very uniform in edited film because of it
(Loschky et al. 2015, "tyranny of film"; Smith 2012).

| Factor | Why it matters | How to get it |
|---|---|---|
| **Focus / depth of field** | The sharp object is the subject; a blurred background is not | Local sharpness / defocus estimation |
| Camera following an object | If the camera pans to keep something in frame, that thing is the subject | Compare camera motion with object motion |
| Zoom-in and close-ups | Zooming or cutting to a close-up announces importance | Object area jump across a cut or over time |
| Framing (rule of thirds, filling the frame) | The composed subject sits at known positions | Position prior |
| Shot cuts | After a cut, gaze resets to the centre and then to the new subject; importance from before the cut may not carry over | Shot boundary detection (TransNetV2) |
| Lighting | The lit subject vs dark surroundings | Brightness map |

## References

- Cerf, Harel, Einhäuser, Koch (2008). Predicting human gaze using low-level saliency combined with face detection. NeurIPS.
- Frischen, Bayliss, Tipper (2007). Gaze cueing of attention. Psychological Bulletin.
- Griffin, Bock (2000). What the eyes say about speaking. Psychological Science.
- Itti, Koch, Niebur (1998). A model of saliency-based visual attention for rapid scene analysis. IEEE TPAMI.
- Land, Hayhoe (2001). In what ways do eye movements contribute to everyday activities? Vision Research.
- Li, Fathi, Rehg (2013). Learning to predict gaze in egocentric video. ICCV.
- Loschky, Larson, Magliano, Smith (2015). What would Jaws do? The tyranny of film and the relationship between gaze and higher-level narrative film comprehension. PLoS ONE.
- Mital, Smith, Hill, Henderson (2011). Clustering of gaze during dynamic scene viewing is predicted by motion. Cognitive Computation.
- Smith (2012). The attentional theory of cinematic continuity. Projections.
- Tatler (2007). The central fixation bias in scene viewing. Journal of Vision.
- Yantis, Jonides (1984). Abrupt visual onsets and selective attention. JEP: Human Perception and Performance.
