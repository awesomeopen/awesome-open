# Category illustration resize workflow

`resize.sh` is an explicit maintenance command. Normal builds copy the committed
WebPs; they do not run it and do not need ImageMagick. This hardening changes no
illustration, brand rule, sharpening setting or committed image bytes.

## Sources and prerequisites

- Use the owner's archived original PNG files. They are not committed, fetched or
  reconstructed by this command. The default original folder is
  `tmp/awesome-open-cat-logos/` under the repository root, regardless of the shell's
  current directory. This folder is intentionally untracked and may be absent.
- [`site/domains/provenance.json`](../site/domains/provenance.json) is the sole
  filename/category mapping. For each of its 21 categories, supply exactly one
  file named either the recorded `source_filename` (including spaces and suffixes)
  or `<category-id>.png`. Do not include both aliases, extra files or subfolders.
  Filenames establish the mapping, not proof of original byte identity.
- Requirements: Bash, Python 3.8+ (standard library only), and ImageMagick **7** with
  PNG read and WebP read/write support, available as `magick` on `PATH`. No packages are
  installed and no network is used. Check `magick -version` and
  `magick -list format` before regeneration.
- The safeguard/recipe tests were validated using ImageMagick **7.1.1-43 Q16**,
  libwebp **1.5.0**, and Python **3.12**. These are validation versions; the original encoding
  environment is unknown. Use a fixed matching toolchain
  when comparing repeated runs; different versions/builds may encode different
  bytes even with the same recipe. Keep committed derivatives unless a reviewed
  regeneration is intended.

## Commands

From the repository root, first validate the complete original set:

```sh
bash scripts/resize.sh --check
```

To generate into a separate existing review folder:

```sh
mkdir -p tmp/category-webp-review
bash scripts/resize.sh --source "/path/to/archived original PNGs" \
  --output tmp/category-webp-review
```

To deliberately replace the committed derivatives after review:

```sh
bash scripts/resize.sh
```

`--source`, `--output` and `--manifest` accept explicit paths. Relative arguments
are relative to the caller's working directory; omitted defaults are relative to
the script's repository. The output folder must already exist and must not overlap
the original folder. `--manifest` defaults to `site/domains/provenance.json` and is
also useful for a bounded synthetic test fixture. `--help` lists the options.

## Preserved recipe

For original width `w`, integer widths are `L = (w*33+50)//100`,
`M = (L+1)//2`, and `S = (M+1)//2`. Each output is resized directly from the same
unchanged original, rather than repeatedly resampling a previous derivative:

```sh
magick original.png -filter Lanczos -distort Resize WIDTH \
  -channel RGB -unsharp 0x0.7+0.7+0.015 +channel \
  -define webp:method=6 -define webp:alpha-quality=100 -quality 88 \
  category-id-SIZE.webp
```

The existing RGB-only sharpening, alpha encoding and l/m/s naming are retained.

## Failure safety and review

The command rejects missing/duplicate/unknown inputs, unsafe manifest names,
symlinked source files or targets, overlapping folders, unreadable PNGs and
unsupported encoders. It snapshots and fully decodes every original before any
generation. All WebPs are generated and decoded in a private staging directory
before replacing a single target. Source hashes are checked again before
publication. An input, generation or validation failure leaves every existing
output byte intact; originals are never opened for writing. Unrelated output
files, including provenance and documentation, are not replaced or removed.

An output-directory lock prevents two instances of this command from running
together. Normal publication errors roll back already replaced targets, restoring
old files and removing newly created ones. If restoration itself fails, the error
identifies a retained backup directory for manual recovery, and the lock remains
until recovery. Replacement is atomic
per file, not across the entire directory: other readers can briefly see a mixed
batch, and forced termination/power loss during publication cannot be made
transactional by this script. Do not edit the input/output folders concurrently.
After a forced stop, inspect any staging/backup directory and confirm no resize
process is active before removing a stale `.category-resize.lock`.

After an intentional successful regeneration, inspect transparency, fine lines
and edges at actual display sizes. Deliberately update the derivative metadata in
`site/domains/provenance.json` and the brand checksum inventory in the same reviewed
change. The script does not rewrite provenance or assert that new bytes match
historical derivatives. Run `python3 scripts/check_brand.py` after those updates.

Focused tests use temporary synthetic PNGs and never touch repository artwork:

```sh
python3 -m unittest discover -s scripts -p 'test_resize_category_images.py' -v
```

ImageMagick integration tests are explicitly skipped when `magick` is unavailable;
the standard-library contract tests still run. No Pillow dependency is required.
