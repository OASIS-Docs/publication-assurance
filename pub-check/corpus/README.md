<!--
Copyright (c) OASIS Open 2026. All Rights Reserved.
Author: Michael Coletta, Technical Advisor to OASIS Open.
-->

# The pinned policy corpus

Every quote in [`../AUTHORITIES.md`](../AUTHORITIES.md) is a verbatim substring
of one of the files in this directory. They are here so that a TC can check the
authority behind a check without taking the catalog's word for it.

`MANIFEST.json` records, for each of the 25 source pages: the URL it was fetched
from, the sha256 of the fetched HTML, its byte length, the name of the plain-text
extraction beside it, and that extraction's character count. The snapshot date is
in the same file.

**The live documents at those URLs are authoritative.** These are dated
snapshots, taken so that a quote can be verified against the text the criterion
was actually derived from. Where a snapshot and the live document disagree, the
live document wins and the criterion needs re-deriving.

`tests/test_authorities.py` checks all of this on every CI run: every digest
against the file it names, every quote as a verbatim substring of the `.txt` it
cites, and every entry in `../crosswalk.json` against the tool's own condition
registry.

```bash
python3 -c "
import hashlib, json, pathlib
m = json.load(open('MANIFEST.json'))['documents']
for name, meta in m.items():
    got = hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest()
    print('ok ' if got == meta['sha256'] else 'BAD', name)"
```

The three governing documents are the OASIS TC Process, the OASIS Committee
Operations Process and the OASIS Naming Directives v1.7; the rest are pages of
the OASIS TC Handbook.
