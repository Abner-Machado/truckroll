# Forced-choice answers with no label map

These are real answers from the first round. They cannot be scored and are not counted
anywhere.

The forced-choice packs show the three checklists under neutral labels S1, S2 and S3. The
map from label to arm lived only in `packs/manifest.json`, and that file is rewritten every
time `jury.py packs` runs. It was rewritten before these answers were scored, so the labels
now decode against a different arrangement and the result is noise.

Kept here because deleting an inconvenient round is worse than admitting one was wasted.
The fix is in `jury.py`: `score` now reads `_manifest.json` from inside the answer tree,
and warns loudly when it has to fall back to the current packs.
