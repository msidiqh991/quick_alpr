# Agent Context & System Memory

## 1. Active Features & Current State
- Pure ALPR HTTP Service: FastAPI accepts an image and returns stateless detection/OCR results. Laravel owns persistence, authentication, authorization, and business workflows.
- Recognition Contract Hardening: Invalid images return HTTP 422, encoded and decoded image sizes are bounded, and OCR responses preserve raw and Indonesian-normalized text.
- Bounded Runtime: One shared recognizer serves one active inference plus a bounded queue; overload and queue timeout responses return HTTP 503.
- Container Runtime: Docker runs one non-root process with a persistent writable model cache outside read-only application and virtual-environment trees.
- Regression Fixture Preparation: Synthetic fixture generation, local real-image categories, and a ground-truth manifest template are available under `tests/fixtures/`.

## 2. Architectural Decision Records (ADR)
- ADR-001 - Stateless ALPR Boundary: Keep this repository limited to image decoding, plate detection, OCR, and response mapping. Do not add Laravel domain logic or persistence.
- ADR-002 - Shared Recognizer Instance: Load one recognizer during FastAPI lifespan and serialize it through the bounded inference runtime to prioritize model safety and predictable memory use over in-process parallelism.
- ADR-003 - Runtime Model Initialization: Initialize and cache model artifacts at application startup rather than coupling the image build to model provider availability.

## 3. Known Blockers & Technical Debt
- Dedicated raw chunked-ASGI middleware and completion-log tests remain deferred; API tests cover body limits and request IDs indirectly.
- Current tests mock inference and do not measure real model accuracy or latency.
- The project configures basedpyright but does not install it as a project dependency.

## 4. Verification & Tooling Commands
- Typecheck: `uvx basedpyright`
- Test Runner: `uv run pytest -q`
- Lint: `uv run ruff check .`
