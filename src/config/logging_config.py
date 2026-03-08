LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "ERROR", "propagate": False},
        "uvicorn.access": {"handlers": [], "level": "CRITICAL", "propagate": False},
        "fastapi": {"handlers": ["default"], "level": "ERROR", "propagate": False},
        "starlette": {"handlers": ["default"], "level": "ERROR", "propagate": False}
    }
}
