# Agent Context & System Memory

## 1. Active Features & Current State
- Pure ALPR HTTP Service: FastAPI accepts an image and returns stateless detection/OCR results. Laravel owns persistence, authentication, authorization, and business workflows.
- Recognition Contract Hardening: Invalid images return HTTP 422 and OCR responses preserve both raw and normalized text.
- Container Runtime: Docker provides production defaults and downloads/caches models at runtime.
- Regression Fixture Preparation: Synthetic fixture generation, local real-image categories, and a ground-truth manifest template are available under `tests/fixtures/`.

## 2. Architectural Decision Records (ADR)
- ADR-001 - Stateless ALPR Boundary: Keep this repository limited to image decoding, plate detection, OCR, and response mapping. Do not add Laravel domain logic or persistence.
- ADR-002 - Shared Recognizer Instance: Load one recognizer during FastAPI lifespan and protect inference with a lock to prioritize model safety and predictable memory use over in-process parallelism.
- ADR-003 - Runtime Model Initialization: Initialize and cache model artifacts at application startup rather than coupling the image build to model provider availability.

## 3. Known Blockers & Technical Debt
- Image upload size is limited, but decoded pixel dimensions are not yet bounded.
- Plate normalization only removes underscores and is not specific to Indonesian plate formats.
- Current tests mock inference and do not measure real model accuracy or latency.
- The project configures basedpyright but does not install it as a project dependency.

## 4. Verification & Tooling Commands
- Typecheck: `uvx basedpyright`
- Test Runner: `uv run pytest -q`
- Lint: `uv run ruff check .`
