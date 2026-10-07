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
- Text subset: 1,863 cropped plate images with `label.csv`

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
uv run python datasets/scripts.py
```

Download another subset:

```bash
uv run python datasets/scripts.py --subset text
uv run python datasets/scripts.py --subset all
```

Preview the first five OCR labels through the Pandas dataset adapter:

```bash
uv run python datasets/scripts.py \
  --subset text \
  --preview-labels
```

Force a fresh download:

```bash
uv run python datasets/scripts.py --force
```

The default detection subset is the most relevant choice for this service
because its images exercise both plate detection and OCR. The text subset is
mostly useful for isolated OCR inspection because its images are already
cropped around a plate.

Review the current Kaggle dataset page and source terms before using the data.
Do not treat the Git ignore rule as a substitute for access control or privacy
requirements.
