import sqlite3

from datetime import datetime
from pathlib import Path


def snapshot(db_path, keep=30):

    source = Path(db_path)

    if not source.exists():

        return None

    folder = source.parent / "backups"
    folder.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = folder / f"{source.stem}-{stamp}.db"

    if target.exists():

        return target

    with sqlite3.connect(str(source)) as src:
        with sqlite3.connect(str(target)) as dst:
            src.backup(dst)

    backups = sorted(folder.glob(f"{source.stem}-*.db"))

    for old in backups[:-keep]:

        old.unlink(missing_ok=True)

    return target
