# ROI Encoding

## Where compression damage shows

Importance says which objects people look at. It does not say how many bits each one needs. Compression
damage such as blur or blockiness is easy to see on a still, smooth surface like a face or a plate, and hard to
see on something moving fast or full of fine detail like sizzling oil or grass. So an important object that
moves fast or is busy texture needs fewer extra bits than its importance alone would suggest. The quality
settings should take both into account.

| Factor | Why it matters | How to get it |
|---|---|---|
| **Spatial masking** | Damage is hidden in busy texture (grass, water) and obvious on smooth areas and edges, and especially on faces and text | Local variance; the encoder's adaptive quantization already does some of this |
| **Temporal masking** | Damage is harder to see in fast motion | Motion magnitude |
| Just noticeable difference (JND) | Below a threshold the extra bits buy nothing visible | JND models (e.g. VideoSet, deep JND) |
| Bit cost | Some objects cost far more bits to sharpen than others | Encoder trial pass |
