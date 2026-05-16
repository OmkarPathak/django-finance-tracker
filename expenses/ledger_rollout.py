from django.conf import settings


def is_user_in_read_cohort(user):
    if not user or not getattr(user, "id", None):
        return False

    if not getattr(settings, "LEDGER_READ_ENABLED", False):
        return False

    include_ids = set(getattr(settings, "LEDGER_READ_COHORT_USER_IDS", set()))
    exclude_ids = set(getattr(settings, "LEDGER_READ_EXCLUDE_USER_IDS", set()))

    if user.id in exclude_ids:
        return False
    if user.id in include_ids:
        return True

    percent = int(getattr(settings, "LEDGER_READ_COHORT_PERCENT", 100))
    if percent <= 0:
        return False
    if percent >= 100:
        return True

    return (user.id % 100) < percent
