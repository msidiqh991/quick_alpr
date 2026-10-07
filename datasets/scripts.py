import argparse
from pathlib import Path

import kagglehub
from kagglehub import KaggleDatasetAdapter

DATASET_HANDLE = "linkgish/indonesian-plate-number-from-multi-sources"
OUTPUT_DIR = Path(__file__).resolve().parent / "indonesian-plates"
LABEL_FILE = "plate_text_dataset/label.csv"
SUBSET_PATHS: dict[str, str | None] = {
    "detection": "plate_detection_dataset",
    "text": "plate_text_dataset",
    "all": None,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download the Indonesian license plate dataset from Kaggle."
    )
    parser.add_argument(
        "--subset",
        choices=SUBSET_PATHS,
        default="detection",
        help="Dataset section to download (default: detection).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Download again and overwrite files already in the output directory.",
    )
    parser.add_argument(
        "--preview-labels",
        action="store_true",
        help="Load label.csv with Pandas and print its first five records.",
    )
    return parser.parse_args()


def download_dataset(subset: str, force_download: bool) -> Path:
    dataset_path = SUBSET_PATHS[subset]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if dataset_path is None:
        downloaded_path = kagglehub.dataset_download(
            DATASET_HANDLE,
            output_dir=str(OUTPUT_DIR),
            force_download=force_download,
        )
    else:
        downloaded_path = kagglehub.dataset_download(
            DATASET_HANDLE,
            path=dataset_path,
            output_dir=str(OUTPUT_DIR),
            force_download=force_download,
        )

    return Path(downloaded_path)


def preview_labels() -> None:
    labels = kagglehub.dataset_load(
        KaggleDatasetAdapter.PANDAS,
        DATASET_HANDLE,
        LABEL_FILE,
    )
    print("First 5 label records:")
    print(labels.head())


def main() -> None:
    args = parse_args()
    downloaded_path = download_dataset(args.subset, args.force)
    print(f"Dataset downloaded to: {downloaded_path}")

    if args.preview_labels:
        preview_labels()


if __name__ == "__main__":
    main()
