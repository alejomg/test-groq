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
            # Obtener el nivel correspondiente en Loguru
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            # Creamos una función interna para parchear el registro de Loguru 
            # con los datos reales del emisor original
            def __patcher(log_record):
                # Si el canal es uvicorn.error, lo renombramos estéticamente
                if record.name == "uvicorn.error":
                    log_record["name"] = "uvicorn"
                else:
                    log_record["name"] = record.name
                
                log_record["file"].name = record.filename
                log_record["file"].path = record.pathname
                log_record["function"] = record.funcName
                log_record["line"] = record.lineno

            # Forzamos a Loguru a usar los metadatos del emisor original
            logger.patch(__patcher).log(level, record.getMessage())
            
    # Lista de loggers de librerías que queremos capturar en Loguru
    loggers_to_intercept = [
        "uvicorn",
        "uvicorn.access",
        "fastapi",
        "sqlalchemy.engine",
        "sqlalchemy.pool"
    ]

    for logger_name in loggers_to_intercept:
        target_logger = logging.getLogger(logger_name)
        
        # 1. Limpiar cualquier handler previo (así matamos el formato clásico con comas)
        for handler in target_logger.handlers[:]:
            target_logger.removeHandler(handler)
            
        # 2. Añadir nuestro interceptor de Loguru
        target_logger.addHandler(InterceptHandler())
        
        # 3. ¡CRUCIAL! Desactivar propagación para evitar duplicados en el root logger de Python
        target_logger.propagate = False

    # Forzar el nivel de SQLAlchemy manualmente ya que quitamos el echo=True
    # Si tu LOGURU_LEVEL es DEBUG o INFO, las consultas se verán a través de Loguru.
    if settings.LOGURU_LEVEL == "DEBUG":
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    else:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Evitar por completo que aiosqlite o asyncio inunden la consola con DEBUG
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
