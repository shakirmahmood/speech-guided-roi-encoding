# Experiments

One folder per experiment: `README.md` (question, how, result, conclusion) and `config.yaml`. Run with
`sgroi-run experiments/<id>`; results go to `runs/<id>/`.

Conclusion format: **verdict** (supported / refuted / inconclusive), **evidence** (key numbers + run
folder), **caveats**, **decision** (what changes because of it).

| ID | Question | Status | Outcome |
|---|---|---|---|
| [e001_box_sanity](e001_box_sanity/README.md) | Does the ROI encoding setup work: zero map identical, box gains at equal bitrate? | done (synthetic clip) | Supported: +1.65 dB in box at 1000 kbps, +1.18 dB at 250 kbps |
