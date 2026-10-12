"""Reset = copy the ORIGINAL database over the working copy.

The original (data/campus_customs.db) is only ever read here, never written.
"""

import shutil

from .config import ORIGINAL_DB, WORKING_DB


def reset_working_db() -> None:
    if not ORIGINAL_DB.exists():
        raise FileNotFoundError(f"Original database missing: {ORIGINAL_DB}")
    shutil.copyfile(ORIGINAL_DB, WORKING_DB)


if __name__ == "__main__":
    reset_working_db()
    print(f"Reset: copied {ORIGINAL_DB.name} over {WORKING_DB.name}.")
