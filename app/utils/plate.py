import re
from collections.abc import Sequence

_SEPARATORS = re.compile(r"[\s_-]+", flags=re.ASCII)
_INDONESIAN_PLATE = re.compile(r"[A-Z]{1,2}[1-9][0-9]{0,3}[A-Z]{0,3}", flags=re.ASCII)


def normalize_plate(value: str) -> str:
    """Normalize case and remove safe visual separators.

    Ambiguous characters such as ``O`` and ``0`` are not substituted.
    """
    return _SEPARATORS.sub("", value.upper())


def is_valid_indonesian_plate(value: str) -> bool:
    """Return whether value has a regular Indonesian plate structure."""
    return _INDONESIAN_PLATE.fullmatch(normalize_plate(value)) is not None


def plates_match(expected: str, predicted: str) -> bool:
    """Return whether two valid normalized plates are equal."""
    expected = normalize_plate(expected)
    predicted = normalize_plate(predicted)

    return (
        expected == predicted
        and is_valid_indonesian_plate(expected)
        and is_valid_indonesian_plate(predicted)
    )


def character_edit_distance(expected: str, predicted: str) -> int:
    """Return the Levenshtein distance between normalized plate values."""
    expected = normalize_plate(expected)
    predicted = normalize_plate(predicted)
    previous = list(range(len(predicted) + 1))

    for row, expected_character in enumerate(expected, start=1):
        current = [row]

        for column, predicted_character in enumerate(predicted, start=1):
            current.append(
                min(
                    current[column - 1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (expected_character != predicted_character),
                )
            )

        previous = current
    return previous[-1]


def best_character_edit_distance(
    expected: str,
    predictions: Sequence[str],
) -> int:
    """Return the smallest edit distance among OCR predictions."""
    return min(
        (character_edit_distance(expected, prediction) for prediction in predictions),
        default=len(normalize_plate(expected)),
    )
