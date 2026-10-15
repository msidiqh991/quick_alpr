# Local Datasets

This directory stores datasets used for local manual and regression testing.
Downloaded files are intentionally excluded from Git because they are large,
can contain vehicle registration data, and remain subject to their source
license and terms.

## Indonesian License Plate Dataset

Source: [Indonesian Vehicle License Plate Dataset](https://www.kaggle.com/datasets/linkgish/indonesian-plate-number-from-multi-sources)

- Kaggle handle: `linkgish/indonesian-plate-number-from-multi-sources`
- Reported license: Apache 2.0
- Reported size: approximately 1.48 GB for the complete dataset
- Detection subset: 1,383 vehicle images with COCO annotations
- Text subset: 1,863 labeled plate crops and full-vehicle images with `label.csv`

Public datasets normally download without authentication. If Kaggle requires
authentication or dataset consent, accept the dataset terms on its Kaggle page
and configure one of the official credential methods:

```text
KAGGLE_API_TOKEN=<token from https://www.kaggle.com/settings/api>
```

Alternatively, store the token in `~/.kaggle/access_token`. Never place a
Kaggle token in this repository or commit it to Git.

Download the detection subset for end-to-end manual API testing:

```bash
uv run python datasets/scripts.py --limit 20
```

Download another subset:

```bash
uv run python datasets/scripts.py --subset text --limit 20
```

Download text images and generate their local benchmark manifest:

```bash
uv run python datasets/scripts.py \
  --subset text \
  --limit 50 \
  --write-text-manifest
```

Regenerate the manifest after updating the downloader or when an existing
manifest does not contain the `input_kind` column. The generated manifest keeps
all valid labeled rows and classifies each image as `plate_crop` or
`full_vehicle`.

Force a fresh download:

```bash
uv run python datasets/scripts.py --limit 20 --force
```

`--limit` is required and counts image files, not annotation or label files.
The downloader requests each selected image individually, so it does not fetch
the complete subset before applying the limit.

Downloaded images use this canonical local layout, independent of the nested
paths used by Kaggle:

```text
datasets/indonesian-plates/
|-- detection/images/
`-- text/
    |-- ground-truth.csv  # Local, generated, ignored by Git
    `-- images/
```

The default detection subset is the most relevant choice for this service
because its images exercise both plate detection and OCR. The text subset is
mostly useful for isolated OCR inspection. The OCR benchmark uses only rows
classified as plate crops and reports how many full-vehicle images it excludes.

Run the OCR benchmark after generating the manifest:

```bash
uv run python tests/benchmark_ocr.py
```

Validate the manifest without loading the OCR model:

```bash
uv run python tests/benchmark_ocr.py --validate-only
```

Compare OCR models without changing `.env`:

```bash
uv run python tests/benchmark_ocr.py --model cct-s-v2-global-model
uv run python tests/benchmark_ocr.py --model global-plates-mobile-vit-v2-model
```

The benchmark performs one OCR pass per plate crop and reports the model name,
status counts, OCR result count, Indonesian format validity, exact match,
corpus character error rate, errors, and latency. It does not perform fuzzy
matching or ambiguous character substitution. Full-vehicle rows remain in the
manifest but are excluded from this crop-only benchmark.

The generated manifest joins downloaded filenames with the official Kaggle
label file. Labels that do not follow the regular Indonesian plate format are
reported and omitted without preventing the CSV from being updated. Filenames
that begin with the normalized expected plate followed by `.` or `_` are
classified as full-vehicle images according to this dataset's naming
convention.

Review the current Kaggle dataset page and source terms before using the data.
Do not treat the Git ignore rule as a substitute for access control or privacy
requirements.
