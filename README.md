# ALPR Service

A stateless FastAPI service that accepts an image, detects license plates,
runs OCR, and returns structured recognition results. Laravel remains the
system of record and owns authentication, authorization, persistence, vehicle
history, access rules, and business workflows.

## Architecture

One recognizer is loaded during application startup and shared by one process.
The bounded inference runtime admits one active request plus a configurable
number of waiting requests, runs exactly one inference at a time, and performs
decode and inference work outside the event loop. Run one Uvicorn worker per
container; scale with additional containers after measuring memory and ONNX
CPU-thread behavior.

```text
Laravel/client
    |
    | POST /plates/recognize (multipart image)
    v
request ID + total-body middleware
    |
    v
bounded admission -> bounded upload read -> Pillow header validation
    |
    v
OpenCV decode -> detector -> OCR -> Indonesian plate normalization
    |
    v
JSON response (raw text, normalized text, confidence, box, image metadata)
```

The service does not persist uploaded images or results. Normalization
uppercases OCR output and removes spaces, underscores, and hyphens. It does not
substitute ambiguous characters such as `O` and `0`.

## Requirements

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/)
- A CPU supported by ONNX Runtime

## Local Development

Create `.env` with the required application and server values:

```dotenv
ALPR_APP_TITLE="ALPR Service"
ALPR_HOST=127.0.0.1
ALPR_PORT=8001
ALPR_RELOAD=true
ALPR_RELOAD_DIR=app
ALPR_DOCS_ENABLED=true
ALPR_DOCS_URL=/docs
ALPR_OPENAPI_URL=/openapi.json
ALPR_DETECTOR_MODEL=yolo-v9-t-640-license-plate-end2end
ALPR_OCR_MODEL=cct-s-v2-global-model
```

Install dependencies and start the development server:

```bash
uv sync
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Run the production entry point locally with `uv run start`. The first startup
downloads model files; later startups reuse the model cache.

## Configuration

All application environment variables use the `ALPR_` prefix.

| Variable | Default | Purpose |
|---|---:|---|
| `ALPR_APP_TITLE` | required | FastAPI application title |
| `ALPR_HOST` | required | Server bind interface |
| `ALPR_PORT` | required | HTTP port |
| `ALPR_RELOAD` | required | Development auto-reload |
| `ALPR_RELOAD_DIR` | required | Directory watched during reload |
| `ALPR_DOCS_ENABLED` | required | Enable OpenAPI, Swagger UI, and ReDoc |
| `ALPR_DOCS_URL` | disabled | Swagger UI URL |
| `ALPR_REDOC_URL` | disabled | ReDoc URL |
| `ALPR_OPENAPI_URL` | disabled | OpenAPI schema URL |
| `ALPR_DETECTOR_MODEL` | required | Detector model identifier |
| `ALPR_OCR_MODEL` | required | OCR model identifier |
| `ALPR_MAX_UPLOAD_MB` | `5` | Maximum encoded image bytes |
| `ALPR_MAX_TOTAL_REQUEST_MB` | `6` | Maximum complete HTTP request body |
| `ALPR_MAX_IMAGE_WIDTH` | `7680` | Maximum decoded width |
| `ALPR_MAX_IMAGE_HEIGHT` | `4320` | Maximum decoded height |
| `ALPR_MAX_IMAGE_PIXELS` | `25000000` | Maximum decoded pixel count |
| `ALPR_INFERENCE_QUEUE_LIMIT` | `4` | Waiting requests allowed after the active request |
| `ALPR_INFERENCE_QUEUE_TIMEOUT_SECONDS` | `5` | Maximum wait for the active inference slot |
| `ALPR_OVERLOAD_RETRY_AFTER_SECONDS` | `1` | `Retry-After` value on capacity failures |

`ALPR_MAX_TOTAL_REQUEST_MB` must exceed `ALPR_MAX_UPLOAD_MB`. When
`ALPR_DOCS_ENABLED=false`, all API documentation endpoints are disabled.

## API

### Recognition

```http
POST /plates/recognize
Content-Type: multipart/form-data
```

The required multipart field is `image`:

```bash
curl -i http://127.0.0.1:8001/plates/recognize \
  -F "image=@vehicle.jpg"
```

A successful response has `status: "success"` and a `data` object containing
`plates`, `image`, and `processing_time`. Each plate includes `plate_number`
(normalized text), `raw_text`, OCR and detection confidence, and `bbox`. A
valid image with no readable plate returns `200` with an empty `plates` list.

Every HTTP response includes `X-Request-ID`. A caller may supply one
`X-Request-ID` containing 1 to 64 ASCII characters: the first must be a letter
or digit, and later characters may also be dots, underscores, colons, or
hyphens. Invalid or duplicate values are replaced. Send this ID when
correlating client failures with service logs.

| Status | Condition |
|---:|---|
| `200` | Recognition completed, including no-plate results |
| `400` | Invalid `Content-Length` header |
| `413` | Total body, encoded image, or decoded dimensions exceed a limit |
| `422` | Missing multipart field or unreadable image |
| `503` | Admission capacity is full or queue wait timed out |
| `500` | Unexpected internal or inference failure |

`503` responses include `Retry-After` in seconds. Clients should wait at least
that long and retry only a limited number of times.

### Health

| Route | Meaning |
|---|---|
| `GET /health` | Compatibility alias for readiness; returns `503` until ready |
| `GET /health/live` | Process liveness; does not access the model |
| `GET /health/ready` | Readiness; `200` after model initialization, otherwise `503` |

Use liveness to restart a stuck process and readiness to control traffic. The
container health check uses `/health/live`; an ingress or orchestrator should
also gate traffic on `/health/ready`.

## Docker

Build and publish only to loopback for local use:

```bash
docker build -t alpr-service .
docker volume create alpr-model-cache
docker run --rm \
  -p 127.0.0.1:8001:8001 \
  -v alpr-model-cache:/var/cache/alpr \
  --cpus=2 \
  --memory=2g \
  alpr-service
```

The container runs as a non-root user. `/app` and `/opt/venv` are root-owned
and not writable by that user; `/var/cache/alpr` is the only writable model
cache. The image starts one Uvicorn worker through the `start` entry point.
Keep the persistent volume so replacements do not download models again.

Set ingress and proxy body limits to `ALPR_MAX_TOTAL_REQUEST_MB`, or to an
intentionally lower limit, including multipart overhead. Also set deployment
CPU and memory limits from measured cold-start and inference usage. Do not
publish this unauthenticated service directly to a public interface; place it
on a private network behind the authenticated application or ingress.

The base image and `uv` image use version tags rather than unverified digests.
As a release verification step on a Docker-enabled host, resolve trusted
publisher digests, review them, and pin both `FROM` references without changing
their selected versions.

### Container verification

Cold-cache check:

```bash
docker volume rm alpr-model-cache 2>/dev/null || true
docker volume create alpr-model-cache
docker run -d --name alpr-cold \
  -p 127.0.0.1:8001:8001 \
  -v alpr-model-cache:/var/cache/alpr \
  alpr-service
until curl -f http://127.0.0.1:8001/health/ready; do sleep 2; done
docker logs alpr-cold
docker rm -f alpr-cold
```

Repeat the detached run and readiness loop with the existing volume and a new
container name, then confirm its logs reach readiness without downloading the
models. Check liveness separately with
`curl -f http://127.0.0.1:8001/health/live`. Check runtime permissions with:

```bash
docker run --rm --entrypoint sh alpr-service -c \
  'test ! -w /app && test ! -w /opt/venv && test -w /var/cache/alpr'
```

## Laravel Integration

Laravel should enforce a client timeout, use limited retries, and evaluate
recognition confidence before making an automated decision:

```php
$response = Http::timeout(30)
    ->attach('image', fopen($imagePath, 'r'), basename($imagePath))
    ->post(config('services.alpr.url').'/plates/recognize')
    ->throw()
    ->json();
```

## Verification

```bash
uv run pytest -q
uv run ruff check .
uvx basedpyright
uv run python tests/benchmark_ocr.py --validate-only
git diff --check
```

Synthetic fixtures cover API behavior, not model accuracy. Dataset preparation
and provenance rules are documented in
[`tests/fixtures/README.md`](tests/fixtures/README.md) and
[`datasets/README.md`](datasets/README.md).

## Current Limitations

- Inference is CPU-only and serialized per container.
- Capacity counters are in memory and reset when the process restarts.
- Automated tests mock inference and are not a model-accuracy benchmark.
- The service does not provide authentication, persistence, or business logic.
