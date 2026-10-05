# ALPR Service

A stateless Python microservice for Automatic License Plate Recognition (ALPR).
The service accepts an image, detects license plates, runs OCR, and returns a
structured result through an HTTP API.

This service is responsible only for ALPR processing. Laravel remains the
system of record and owns authentication, authorization, persistence, vehicle
history, allowlists/blocklists, and all business workflows.

## System Responsibilities

### Python ALPR service

- Accept an image as `multipart/form-data`.
- Enforce the configured upload-size limit.
- Decode image bytes into an OpenCV BGR image.
- Run plate detection and OCR through `fast-alpr`.
- Return raw and normalized text, confidence scores, bounding boxes, image
  metadata, and processing time.
- Never persist uploaded images or recognition results.

### Laravel application

- Authenticate and authorize users, services, and devices.
- Store images and recognition results when required.
- Manage vehicles, owners, access rules, allowlists, and blocklists.
- Implement parking, gate, notification, audit, and reporting workflows.
- Call the ALPR service and make business decisions from its response.

## Request Flow

```text
Laravel/client
    |
    | POST /plates/recognize (multipart image)
    v
FastAPI router
    |
    +-- validate upload size
    +-- decode image with OpenCV
    v
PlateRecognizer
    |
    +-- license plate detection
    +-- OCR
    +-- text normalization
    v
JSON response
```

The model is loaded once during application startup and stored in `app.state`.
Inference is protected by a lock because requests within one process share the
same model instance.

## Project Structure

```text
alpr_system/
|-- app/
|   |-- core/
|   |   `-- config.py              # Environment-based configuration
|   |-- routers/
|   |   |-- health.py              # Health endpoint
|   |   `-- plates.py              # Recognition endpoint
|   |-- schemas/
|   |   `-- plates.py              # Pydantic response models
|   |-- services/
|   |   `-- plate_recognizer.py    # Detection and OCR adapter
|   |-- utils/
|   |   `-- image.py               # OpenCV image decoder
|   |-- dependencies.py            # FastAPI dependency injection
|   `-- main.py                    # Application and lifespan
|-- tests/
|   |-- fixtures/
|   |   |-- expected/              # Ground-truth manifest templates
|   |   |-- real/                  # Local real-image regression dataset
|   |   `-- synthetic/             # Generated deterministic fixtures
|   `-- test_plates.py
|-- typings/
|   `-- fast_alpr/                 # Local type declarations
|-- Dockerfile
|-- pyproject.toml
`-- uv.lock
```

## Requirements

- Python 3.11 or newer.
- [uv](https://docs.astral.sh/uv/) for dependency and environment management.
- A CPU supported by the ONNX runtime. The current configuration uses CPU
  inference.

## Local Development

Create a `.env` file with the following configuration:

```dotenv
ALPR_APP_TITLE="ALPR Service"
ALPR_RELOAD=true
ALPR_RELOAD_DIR=app
ALPR_DOCS_URL=/docs
ALPR_OPENAPI_URL=/openapi.json
ALPR_DOCS_ENABLED=true

ALPR_HOST=127.0.0.1
ALPR_PORT=8001
ALPR_DETECTOR_MODEL=yolo-v9-t-640-license-plate-end2end
ALPR_OCR_MODEL=cct-xs-v2-global-model
ALPR_MAX_UPLOAD_MB=5
```

Install dependencies and start the development server:

```bash
uv sync
uv run dev
```

Run the local production entry point:

```bash
uv run start
```

The model may be downloaded by the underlying library during the first
startup. Later startups reuse the available model cache.

## Configuration

All environment variables use the `ALPR_` prefix.

| Variable | Purpose |
|---|---|
| `ALPR_APP_TITLE` | FastAPI application title |
| `ALPR_HOST` | Server bind interface |
| `ALPR_PORT` | HTTP port |
| `ALPR_RELOAD` | Enable development auto-reload |
| `ALPR_RELOAD_DIR` | Directory watched by auto-reload |
| `ALPR_DOCS_ENABLED` | Enable OpenAPI, Swagger UI, and ReDoc |
| `ALPR_DOCS_URL` | Swagger UI URL |
| `ALPR_REDOC_URL` | Optional ReDoc URL |
| `ALPR_OPENAPI_URL` | OpenAPI schema URL |
| `ALPR_DETECTOR_MODEL` | License plate detector model |
| `ALPR_OCR_MODEL` | OCR model |
| `ALPR_MAX_UPLOAD_MB` | Maximum upload size in MB |

When `ALPR_DOCS_ENABLED=false`, all API documentation endpoints are disabled,
even if their URLs are configured.

## API

### Health check

```http
GET /health
```

Response `200 OK`:

```json
{
  "status": "ok"
}
```

### Recognize plates

```http
POST /plates/recognize
Content-Type: multipart/form-data
```

Required field: `image`.

Example request:

```bash
curl -X POST "http://127.0.0.1:8001/plates/recognize" \
  -F "image=@vehicle.jpg"
```

Example `200 OK` response:

```json
{
  "status": "success",
  "data": {
    "plates": [
      {
        "plate_number": "B1234ABC",
        "raw_text": "B_1234_ABC",
        "plate_confidence": 0.9,
        "detection_confidence": 0.95,
        "bbox": {
          "x1": 100,
          "y1": 200,
          "x2": 320,
          "y2": 270
        }
      }
    ],
    "image": {
      "filename": "vehicle.jpg",
      "content_type": "image/jpeg",
      "width": 1920,
      "height": 1080
    },
    "processing_time": 0.42
  }
}
```

`plate_number` is currently the `raw_text` value with underscores removed. If
no readable plate is found, the request still succeeds and `plates` is empty.

### Error responses

| Status | Condition |
|---|---|
| `413` | File exceeds `ALPR_MAX_UPLOAD_MB` |
| `422` | Image field is missing or the file cannot be decoded as an image |
| `500` | Unexpected internal or inference failure |

## Laravel Integration

Laravel can forward a file to this service and persist the response according
to domain requirements. Laravel should enforce a timeout, use limited retries,
and evaluate recognition confidence before making an automated decision.

```php
$response = Http::timeout(30)
    ->attach('image', fopen($imagePath, 'r'), basename($imagePath))
    ->post(config('services.alpr.url').'/plates/recognize')
    ->throw()
    ->json();
```

Deploy the service on a private network and allow access only from Laravel or
other trusted internal components. The service does not implement its own
authentication because access control belongs to the Laravel application
layer.

## Test Image Preparation

The fixture layout and dataset rules are documented in
[`tests/fixtures/README.md`](tests/fixtures/README.md).

Generate deterministic synthetic fixtures:

```bash
uv run python tests/fixtures/generate_synthetic.py
```

Synthetic images validate decoding, error handling, response schemas, and the
no-plate path. They are not representative enough to measure OCR accuracy.

For model regression, use approved real images captured from the intended
camera setup whenever possible. A useful initial dataset contains clear,
multiple-plate, no-plate, blurry, low-light, angled, and partially visible
examples. Copy the example manifest before recording expected values:

```bash
cp tests/fixtures/expected/plates.example.json \
  tests/fixtures/expected/plates.local.json
```

`plates.local.json` and real image files are ignored by Git to reduce the risk
of committing personal or licensed data.

Do not use random Google Images as the primary regression dataset. Search
results usually have unclear redistribution rights, inconsistent provenance,
and image characteristics that differ from the deployment camera. If a search
image is used for temporary exploration, verify its license, record its source,
and do not commit or redistribute it without permission.

Preferred sources, in order:

1. Images captured from the actual deployment camera with organizational and
   privacy approval.
2. An internally approved and anonymized operational dataset.
3. Public datasets with an explicit license that permits the intended use.
4. Synthetic images for API behavior only, not model accuracy claims.

## Docker

Build the image:

```bash
docker build -t alpr-service .
```

Run the container:

```bash
docker run --rm -p 8001:8001 alpr-service
```

The container defaults bind to `0.0.0.0:8001`, disable development reload and
API documentation, and use the same models as local development. Override any
value with `-e` or `--env-file`.

Persist the model cache between containers:

```bash
docker run --rm -p 8001:8001 \
  -v alpr-model-cache:/app/.cache \
  alpr-service
```

## Verification

Run unit and API contract tests:

```bash
uv run pytest -q
```

Run lint checks:

```bash
uv run ruff check .
```

Run type checking without adding a project dependency:

```bash
uvx basedpyright
```

Manual and regression API checks can also be maintained as a Bruno collection.
At minimum, include health, valid image, no plate, corrupt image, missing image,
and oversized image requests.

## Current Limitations

- Inference runs on CPU.
- The lock serializes inference within one process.
- Normalization currently removes only underscores from OCR text.
- Decompressed image dimensions are not yet bounded.
- Automated tests mock inference and are not a model-accuracy benchmark.
- The service does not manage databases, vehicle domains, or business flows.

## References

- [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/)
- [FastAPI file uploads](https://fastapi.tiangolo.com/tutorial/request-files/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [uv documentation](https://docs.astral.sh/uv/)
