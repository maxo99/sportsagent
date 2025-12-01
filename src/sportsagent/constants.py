from datetime import datetime

CURRENT_YEAR = datetime.now().year
CURRENT_SEASON = CURRENT_YEAR if datetime.now().month >= 9 else CURRENT_YEAR - 1

