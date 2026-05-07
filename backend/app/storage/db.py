from typing import Generator, Optional


def get_db() -> Generator[Optional[object], None, None]:
    yield None
