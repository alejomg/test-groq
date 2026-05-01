import logging
import sys
from loguru import logger
from app.core.config import settings


def setup_logging():
    # Eliminar los manejadores por defecto de Loguru
    logger.remove()

    # Añadir manejador (sink) para la consola con un formato limpio
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOGURU_LEVEL,
    )

    # Opcional: Añadir un archivo con rotación
    #logger.add("logs/app.log", rotation="500 MB", retention="10 days", compression="zip", level="DEBUG")

    # Interceptar logs del sistema (logging estándar)
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    # Aplicar la interceptación a los loggers de FastAPI y Uvicorn
    logging.getLogger("uvicorn").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
    logging.getLogger("fastapi").handlers = [InterceptHandler()]
