from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from expenses.ledger_rollout import is_user_in_read_cohort


class Command(BaseCommand):
    help = "Show how many users are currently in ledger-read cohort"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="Sample only first N users (0 = all)")

    def handle(self, *args, **options):
        User = get_user_model()
        users = User.objects.filter(is_active=True).order_by("id")
        if options["limit"] and options["limit"] > 0:
            users = users[: options["limit"]]

        total = 0
        in_cohort = 0
        sample_ids = []

        for user in users:
            total += 1
            if is_user_in_read_cohort(user):
                in_cohort += 1
                if len(sample_ids) < 20:
                    sample_ids.append(user.id)

        pct = (in_cohort / total * 100) if total else 0
        self.stdout.write(self.style.SUCCESS(f"Ledger read cohort: {in_cohort}/{total} users ({pct:.1f}%)"))
        if sample_ids:
            self.stdout.write(f"Sample user IDs in cohort: {sample_ids}")
