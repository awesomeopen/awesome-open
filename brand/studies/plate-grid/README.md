# Plate evidence grid study

Mock-up for the specimen plate's lower half: a fixed box grid replacing the
stacked bands below the function and specimen. Owner-directed, iterated on
2026-10-20/21. Not deployed; the generator and stylesheet are unchanged until an
implementation PR. The decision is recorded in [`brand/decisions/`](../../decisions/).

## Files

| File | What it shows |
| --- | --- |
| `opentofu-grid.png` | Fullest record (1440px): every evidence type except a returned Scorecard result, one alternative |
| `openstatus-grid.png` | Three alternatives filling the row in thirds |
| `opengeosys-grid.png` | Sparse record, not on GitHub: same geometry, “Unknown” values, collapsed timeline, no alternatives row |
| `opentofu-grid-phone.png` | One column at 390px; empty boxes hidden |
| `mock_plate_grid.py` | Generator for the three HTML mock-ups |

The screenshots are cropped to the grid. Values are real catalog data from the
generated site at the source revision named in the decision record; they will
drift from the live catalog.

## Regenerate

```sh
python3 scripts/build_site.py --output tmp/site
python3 brand/studies/plate-grid/mock_plate_grid.py
python3 -m http.server 8000 --directory tmp/site
```

Open `http://localhost:8000/records/mock-grid-opentofu.html` (also
`mock-grid-openstatus.html`, `mock-grid-opengeosys.html`). The generator keeps the
generated record above the first plate band and rewrites the bands only; it does
not modify generated pages other than its own three outputs. The OpenTofu page
ends with a Scorecard box using OpenSCAD's returned result, because no record
has every evidence type.
