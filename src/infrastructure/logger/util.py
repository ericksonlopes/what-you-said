import inspect
import os
from datetime import datetime


def get_logger_module_files(base_dir=None):
    """
    Returns a set with normalized (absolute) paths of ALL .py files
    inside src/infrastructure/logger, including subdirectories.
    This list adapts dynamically to all files present in the logger infra.
    """
    # Automatically determines the absolute logger directory, even if the project is moved
    if base_dir is None:
        base_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__))
        )
    logger_files = set()
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.py'):
                logger_files.add(os.path.abspath(os.path.join(root, file)))
    return logger_files


def get_log_record(level: str, message: str):
    """
    Extracts detailed context from the frame where the log was originally called.
    Returns a dict with all fields for the standard log template.
    This context excludes any frame from infrastructure python files found in the logger directory.
    """
    logger_files = get_logger_module_files()
    stack = inspect.stack()
    cls_name = ""
    frame_best = stack[1]
    for frame_info in stack:
        filename_abs = os.path.abspath(frame_info.filename)
        # Ignore all frames in infra/logger (dynamic detection)
        if filename_abs not in logger_files:
            self_obj = frame_info.frame.f_locals.get('self', None)
            if self_obj:
                cls_name = type(self_obj).__name__
            frame_best = frame_info
            break

    asctime = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
    filename = os.path.basename(frame_best.filename)
    filepath = os.path.abspath(frame_best.filename)
    lineno = frame_best.lineno
    func_name = frame_best.function

    return {
        'asctime': asctime,
        'levelname': level.upper(),
        'filename': filename,
        'filepath': filepath,
        'lineno': lineno,
        'class': cls_name,
        'funcName': func_name,
        'message': message
    }
