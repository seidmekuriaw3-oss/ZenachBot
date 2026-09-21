import logging
from pathlib import Path


def setup_logger(name: str = 'zenach_bot') -> logging.Logger:
	"""Configure and return a named application logger."""
	logger = logging.getLogger(name)
	if logger.handlers:
		return logger

	log_dir = Path('logs')
	log_dir.mkdir(parents=True, exist_ok=True)

	formatter = logging.Formatter(
		'%(asctime)s - %(name)s - %(levelname)s - %(message)s'
	)
	handler = logging.StreamHandler()
	handler.setFormatter(formatter)
	logger.addHandler(handler)
	logger.setLevel(logging.INFO)
	logger.propagate = False
	return logger


def get_logger(name: str = 'zenach_bot') -> logging.Logger:
	return setup_logger(name)


def log_error(message: str, name: str = 'zenach_bot') -> None:
	get_logger(name).error(message)


def log_info(message: str, name: str = 'zenach_bot') -> None:
	get_logger(name).info(message)


def log_warning(message: str, name: str = 'zenach_bot') -> None:
	get_logger(name).warning(message)


def log_debug(message: str, name: str = 'zenach_bot') -> None:
	get_logger(name).debug(message)
