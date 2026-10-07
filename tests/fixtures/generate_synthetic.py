from pathlib import Path

import cv2
import numpy as np

OUTPUT_DIR = Path(__file__).parent / "synthetic"
IMAGE_HEIGHT = 720
IMAGE_WIDTH = 1280


def write_image(filename: str, image: np.ndarray) -> None:
    output_path = OUTPUT_DIR / filename
    written = cv2.imwrite(str(output_path), image)
    if not written:
        raise RuntimeError(f"Failed to write synthetic fixture: {output_path}")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    shape = (IMAGE_HEIGHT, IMAGE_WIDTH, 3)
    write_image("black.png", np.zeros(shape, dtype=np.uint8))
    write_image("white.png", np.full(shape, 255, dtype=np.uint8))

    random = np.random.default_rng(seed=42)
    noise = random.integers(0, 256, size=shape, dtype=np.uint8)
    write_image("noise.png", noise)

    (OUTPUT_DIR / "corrupt.jpg").write_bytes(b"not-an-image")


if __name__ == "__main__":
    main()
