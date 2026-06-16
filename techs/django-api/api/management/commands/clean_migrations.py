import os
from pathlib import Path

from django.core.management.base import BaseCommand
from django.apps import apps


class Command(BaseCommand):
    help = "Delete all migration files (except __init__.py) for all installed apps."

    def add_arguments(self, parser):
        parser.add_argument(
            "app_labels",
            nargs="*",
            help="App labels to clean. Defaults to all installed apps.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show which files would be deleted without actually deleting them.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        app_labels = options["app_labels"]

        target_apps = [
            config for config in apps.get_app_configs()
            if not app_labels or config.label in app_labels
        ]

        if not target_apps:
            self.stderr.write(self.style.ERROR("No matching apps found."))
            return

        deleted = 0

        for config in target_apps:
            migrations_dir = Path(config.path) / "migrations"
            if not migrations_dir.is_dir():
                continue

            for migration_file in sorted(migrations_dir.iterdir()):
                if (
                    migration_file.is_file()
                    and migration_file.suffix == ".py"
                    and migration_file.name != "__init__.py"
                ):
                    if dry_run:
                        self.stdout.write(f"  [dry-run] would delete: {migration_file}")
                    else:
                        migration_file.unlink()
                        self.stdout.write(self.style.WARNING(f"  deleted: {migration_file}"))
                    deleted += 1

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"\n{deleted} file(s) would be deleted (dry-run)."))
        else:
            self.stdout.write(self.style.SUCCESS(f"\n{deleted} migration file(s) deleted."))
            self.stdout.write("Run 'python manage.py makemigrations' to regenerate them.")
