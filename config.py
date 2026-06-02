from datetime import datetime

WARNINGS_PATH="log_and_warn/warnings"
LOG_PATH="log_and_warn/log"
date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

RUN_LOG_FILENAME=f"{LOG_PATH}/{date_str}_running_log.json"
WARNING_FILENAME=f"{WARNINGS_PATH}/{date_str}_warnings.txt"

