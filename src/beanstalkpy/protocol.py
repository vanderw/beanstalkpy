from typing import Final

DEFAULT_HOST: Final = "0.0.0.0"
DEFAULT_PORT: Final = 11300

CRLF: Final = b"\r\n"

# Job Priorities
PRIORITY_URGENT: Final = 0
PRIORITY_DEFAULT: Final = 1024
PRIORITY_LOW: Final = 4294967295

# Job TTR
DEFAULT_TTR: Final = 60

# Max values
MAX_PRIORITY: Final = 2**32 - 1
MAX_TTR: Final = 2**32 - 1
MAX_DELAY: Final = 2**32 - 1
MAX_NAME_LENGTH: Final = 200
MAX_COMMAND_LINE_LENGTH: Final = 224
