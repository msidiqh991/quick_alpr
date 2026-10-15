import argparse
import csv
import json
import shutil
from enum import StrEnum
from http.client import HTTPResponse
from pathlib import Path
from typing import TypedDict, cast
from urllib.parse import urlencode
from urllib.request import urlopen

import kagglehub

from app.utils.plate import is_valid_indonesian_plate, normalize_plate

OUTPUT_DIR = Path(__file__).resolve().parent / "indonesian-plates"

IMAGE_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp"})

TEXT_MANIFEST = OUTPUT_DIR / "text/ground-truth.csv"

DATASET_HANDLE = "linkgish/indonesian-plate-number-from-multi-sources"

DATASET_FILES_URL = f"https://www.kaggle.com/api/v1/datasets/list/{DATASET_HANDLE}"
TEXT_LABEL_REMOTE_PATH = "plate_text_dataset/plate_text_dataset/label.csv"


class DatasetSubset(StrEnum):
    DETECTION = "detection"
    TEXT = "text"


class InputKind(StrEnum):
    PLATE_CROP = "plate_crop"
    FULL_VEHICLE = "full_vehicle"


class DatasetFile(TypedDict):
    name: str


class DatasetPage(TypedDict, total=False):
    datasetFiles: list[DatasetFile]
    nextPageToken: str


class CliArgs(argparse.Namespace):
    subset: DatasetSubset = DatasetSubset.DETECTION
    limit: int = 0
    force: bool = False
    write_text_manifest: bool = False


SUBSET_PATHS = {
    DatasetSubset.DETECTION: "plate_detection_dataset",
    DatasetSubset.TEXT: "plate_text_dataset",
}
SUBSET_OUTPUT_DIRS = {
    DatasetSubset.DETECTION: OUTPUT_DIR / "detection/images",
    DatasetSubset.TEXT: OUTPUT_DIR / "text/images",
}


def classify_input_kind(filename: str, expected_plate: str) -> InputKind:
    """Classify an image using the dataset's filename convention."""
    normalized_plate = normalize_plate(expected_plate)
    normalized_filename = Path(filename).name.upper()
    full_image_prefixes = (f"{normalized_plate}.", f"{normalized_plate}_")

    if normalized_filename.startswith(full_image_prefixes):
        return InputKind.FULL_VEHICLE
    return InputKind.PLATE_CROP


def list_image_paths(subset: DatasetSubset, limit: int) -> list[str]:
    """List a limited number of image paths from the Kaggle dataset."""
    image_paths: list[str] = []
    page_token: str | None = None
    seen_tokens: set[str] = set()

    while len(image_paths) < limit:
        parameters = {"pageSize": "100"}
        if page_token is not None:
            parameters["pageToken"] = page_token

        url = f"{DATASET_FILES_URL}?{urlencode(parameters)}"
        raw_response = cast(HTTPResponse, urlopen(url, timeout=30))
        with raw_response as response:
            page = cast(DatasetPage, json.loads(response.read()))

        for dataset_file in page.get("datasetFiles", []):
            file_path = dataset_file["name"]
            if not file_path.startswith(f"{SUBSET_PATHS[subset]}/"):
                continue
            if Path(file_path).suffix.lower() not in IMAGE_SUFFIXES:
                continue

            image_paths.append(file_path)
            if len(image_paths) == limit:
                return image_paths

        page_token = page.get("nextPageToken")
        if not page_token:
            break
        if page_token in seen_tokens:
            raise RuntimeError("Kaggle API returned a repeated page token")

        seen_tokens.add(page_token)

    if len(image_paths) < limit:
        raise RuntimeError(
            f"Requested {limit} images, found {len(image_paths)} in {subset}."
        )

    return image_paths


def download_dataset(
    subset: DatasetSubset,
    limit: int,
    *,
    force: bool = False,
) -> list[Path]:
    """Download selected images into the canonical local directory."""
    destination_dir = SUBSET_OUTPUT_DIRS[subset]
    destination_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[Path] = []

    for remote_path in list_image_paths(subset, limit):
        destination = destination_dir / Path(remote_path).name
        if not destination.exists() or force:
            cached_path = Path(
                kagglehub.dataset_download(
                    DATASET_HANDLE,
                    path=remote_path,
                    force_download=force,
                )
            )
            _ = shutil.copy2(cached_path, destination)

        downloaded.append(destination)

    return downloaded


def write_manifest(image_paths: list[Path]) -> tuple[Path, int]:
    """Write valid official OCR labels and return the skipped row count."""
    label_path = Path(
        kagglehub.dataset_download(
            DATASET_HANDLE,
            path=TEXT_LABEL_REMOTE_PATH,
        )
    )
    labels: dict[str, str] = {}
    with label_path.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            filename = row.get("filename")
            label = row.get("label")
            if filename and label:
                labels[filename] = normalize_plate(label)

    rows: list[tuple[str, str, InputKind]] = []
    skipped = 0

    for image_path in image_paths:
        expected_plate = labels.get(image_path.name)
        if expected_plate is None:
            print(f"Skipped {image_path.name}: label not found")
            skipped += 1
            continue
        if not is_valid_indonesian_plate(expected_plate):
            print(f"Skipped {image_path.name}: invalid label {expected_plate}")
            skipped += 1
            continue

        rows.append(
            (
                image_path.name,
                expected_plate,
                classify_input_kind(image_path.name, expected_plate),
            )
        )

    temporary_manifest = TEXT_MANIFEST.with_suffix(".tmp")
    with temporary_manifest.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(("filename", "expected_plate", "input_kind"))
        writer.writerows(rows)
    _ = temporary_manifest.replace(TEXT_MANIFEST)

    return TEXT_MANIFEST, skipped


def main() -> None:
    """Download a dataset subset and optionally generate an OCR manifest."""
    parser = argparse.ArgumentParser(
        description="Download Indonesian license-plate images from Kaggle."
    )
    _ = parser.add_argument(
        "--subset",
        type=DatasetSubset,
        choices=DatasetSubset,
        default=DatasetSubset.DETECTION,
    )
    _ = parser.add_argument("--limit", type=int, required=True)
    _ = parser.add_argument("--force", action="store_true")
    _ = parser.add_argument("--write-text-manifest", action="store_true")
    args = CliArgs()
    _ = parser.parse_args(namespace=args)

    if args.limit < 1:
        parser.error("--limit must be greater than zero")
    if args.write_text_manifest and args.subset is not DatasetSubset.TEXT:
        parser.error("--write-text-manifest requires --subset text")

    downloaded = download_dataset(
        args.subset,
        args.limit,
        force=args.force,
    )
    print(f"Prepared {len(downloaded)} images under: {OUTPUT_DIR}")

    if args.write_text_manifest:
        manifest, skipped = write_manifest(downloaded)
        print(f"Text manifest written to: {manifest}")
        print(f"Manifest rows: {len(downloaded) - skipped}; skipped: {skipped}")


if __name__ == "__main__":
    main()
