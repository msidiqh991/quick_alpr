# ALPR Test Fixtures

This directory separates deterministic API fixtures from real images used to
measure model behavior.

## Layout

```text
fixtures/
|-- expected/
|   `-- plates.example.json
|-- real/
|   |-- angled/
|   |-- blurry/
|   |-- low-light/
|   |-- multiple-plates/
|   |-- no-plate/
|   |-- partial/
|   `-- single-clear/
|-- synthetic/
`-- generate_synthetic.py
```

## Synthetic Fixtures

Generate deterministic fixtures with:

```bash
uv run python tests/fixtures/generate_synthetic.py
```

The command creates:

| File | Intended assertion |
|---|---|
| `black.png` | Valid image with no expected plate |
| `white.png` | Valid image with no expected plate |
| `noise.png` | Valid decodable image; do not require an OCR result |
| `corrupt.jpg` | Must return HTTP 422 |

These images test transport, decoding, error handling, and response structure.
They do not provide a meaningful OCR-accuracy benchmark.

## Real Fixtures

Use real images for model regression. Start with at least five approved images
per category, then expand the dataset based on production failure cases.

| Category | Purpose |
|---|---|
| `single-clear` | Basic successful recognition |
| `multiple-plates` | Multiple detections and result ordering |
| `no-plate` | False-positive monitoring |
| `blurry` | Motion or focus blur |
| `low-light` | Night and poor illumination |
| `angled` | Perspective and camera-angle variation |
| `partial` | Cropped or obstructed plates |

Recommended file names do not expose plate values:

```text
real-001.jpg
real-002.jpg
real-003.jpg
```

Real image extensions in this directory are ignored by Git. This prevents
accidental commits, but it does not replace proper privacy controls, access
permissions, retention limits, or licensing review.

## Image Sources

Do not build the primary regression dataset by downloading random Google Image
search results. Search results are discovery links, not a license. They also
rarely represent the actual camera distance, angle, compression, lighting, and
motion conditions of the deployed system.

Use these sources in priority order:

1. Capture images from the intended camera setup after obtaining the necessary
   organizational and privacy approval.
2. Use an approved internal dataset and anonymize unrelated personal details.
3. Use a public dataset only when its explicit license allows your intended
   use; retain the license and source metadata.
4. Use synthetic images only for API and decoder tests.

When collecting deployment images, vary distance, angle, daylight, night,
rain, glare, motion, plate size, motorcycles, cars, and scenes without plates.
Do not include an image only because the current model already recognizes it.
Failure cases are the most valuable regression fixtures.

## Ground Truth

Create the local manifest from the template:

```bash
cp tests/fixtures/expected/plates.example.json \
  tests/fixtures/expected/plates.local.json
```

For every image, record the expected normalized plate and optional expected
bounding box. Keep `plates.local.json` synchronized with the local real-image
dataset. It is ignored by Git because plate values can be sensitive.

Do not assert exact confidence scores or processing times. Use confidence
thresholds and latency ranges because runtime and model updates can introduce
small numerical changes.
