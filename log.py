import logging
import config

# 日志格式
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'

def get_logger(name, filename, level=logging.DEBUG):
    """创建独立日志器的工具函数"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # 阻止日志传播
    
    if logger.handlers:
        return logger
    
    formatter = logging.Formatter(LOG_FORMAT)
    
    # 文件处理器
    file_handler = logging.FileHandler(filename, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger




##一般记录
run_logger = get_logger(
    name="run_logger",
    filename=f"{config.RUN_LOG_FILENAME}",
    level=logging.INFO
)


##警告记录
warning_logger = get_logger(
    name="warning_logger",
    filename=f"{config.WARNING_FILENAME}",
    level=logging.WARNING
)



