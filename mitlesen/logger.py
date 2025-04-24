import logging
import sys

# Set up the logger
logger = logging.getLogger()  # Root logger
logger.setLevel(logging.INFO)

# Create a handler for stdout (INFO and lower)
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
stdout_filter = logging.Filter()
stdout_filter.filter = lambda record: record.levelno <= logging.INFO
stdout_handler.addFilter(stdout_filter)

# Create a handler for stderr (WARNING and above)
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(logging.WARNING)

# Create a formatter and attach it to the handlers
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
stdout_handler.setFormatter(formatter)
stderr_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(stdout_handler)
logger.addHandler(stderr_handler)

# Expose the logger for import
__all__ = ["logger"]
