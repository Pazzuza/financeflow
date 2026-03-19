import os
import sys


def main() -> None:
    # Ensure the installed `alembic` package is imported (our local migration folder is also named `alembic`).
    cwd = os.getcwd()
    if "" in sys.path:
        sys.path.remove("")
        sys.path.append("")
    if cwd in sys.path:
        sys.path.remove(cwd)
        sys.path.append(cwd)

    from alembic.config import Config  # noqa: WPS433
    from alembic import command  # noqa: WPS433

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


if __name__ == "__main__":
    main()

