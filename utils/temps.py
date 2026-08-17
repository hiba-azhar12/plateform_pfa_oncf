from datetime import datetime
from zoneinfo import ZoneInfo

FUSEAU_MAROC = ZoneInfo("Africa/Casablanca")


def maintenant_maroc():
    return datetime.now(FUSEAU_MAROC)


def horodatage_maroc():
    return maintenant_maroc().strftime("%Y-%m-%d %H:%M:%S")


def aujourd_hui_maroc():
    return maintenant_maroc().date()