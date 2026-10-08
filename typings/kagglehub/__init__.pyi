from enum import Enum

class DataFrame:
    def head(self, n: int = 5) -> DataFrame: ...
    def to_string(self, *, index: bool = True) -> str: ...

class KaggleDatasetAdapter(str, Enum):
    PANDAS = "pandas"

def dataset_download(
    handle: str,
    path: str | None = None,
    *,
    force_download: bool | None = False,
    output_dir: str | None = None,
) -> str: ...

def dataset_load(
    adapter: KaggleDatasetAdapter,
    handle: str,
    path: str,
) -> DataFrame: ...
