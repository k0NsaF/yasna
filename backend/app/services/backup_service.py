
import sqlite3
from datetime import datetime
from pathlib import Path


def create_backup():
    """
    Создаёт резервную копию SQLite-базы yasna.db.
    Исходная база не изменяется.
    """

    project_root = Path.cwd()
    database_path = project_root / "yasna.db"
    backup_directory = project_root / "backups"

    if not database_path.exists():
        raise FileNotFoundError(
            f"База данных не найдена: {database_path}"
        )

    backup_directory.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = backup_directory / f"yasna_backup_{timestamp}.db"

    with sqlite3.connect(str(database_path)) as source:
        with sqlite3.connect(str(backup_path)) as destination:
            source.backup(destination)

            result = destination.execute(
                "PRAGMA integrity_check"
            ).fetchone()

            if not result or result[0] != "ok":
                destination.close()
                backup_path.unlink(missing_ok=True)
                raise RuntimeError(
                    "Проверка резервной копии не пройдена"
                )

    return backup_path


def list_backups():
    """Возвращает список резервных копий."""

    backup_directory = Path.cwd() / "backups"

    if not backup_directory.exists():
        return []

    return sorted(
        backup_directory.glob("yasna_backup_*.db"),
        reverse=True
    )


if __name__ == "__main__":
    created_backup = create_backup()
    print("Резервная копия успешно создана:")
    print(created_backup)
