
import configparser
import os


def _load_config():
    """加载并验证配置文件"""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), '../config.ini')

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件未找到: {config_path}")

    config.read(config_path)

    required_sections = {
        'database': ['host', 'user', 'password', 'database', 'port'],
        'paths': ['watch_folder', 'public_folder'],
        'settings': ['check_interval', 'max_retries', 'retry_interval'],
        'server': ['host', 'port']
    }

    for section, keys in required_sections.items():
        if not config.has_section(section):
            raise ValueError(f"缺少配置段落: [{section}]")
        for key in keys:
            if not config.has_option(section, key):
                raise ValueError(f"段落 [{section}] 缺少配置项: {key}")

    return config


def _get_path(section: str, option: str):
    p = config.get(section, option)
    if p is None or p == '':
        return None
    if not os.path.isabs(p):
        p = os.path.join(os.path.dirname(__file__), '..', p)
    return os.path.normpath(p)


try:
    config = _load_config()
except Exception as e:
    print(f"配置加载失败: {str(e)}")
    exit(1)

# 配置信息（保持不变）
DB_CONFIG = {
    'host': config.get('database', 'host'),
    'user': config.get('database', 'user'),
    'password': config.get('database', 'password'),
    'database': config.get('database', 'database'),
    'port': config.getint('database', 'port'),
    'autocommit': True
}

SERVER_HOST = config.get('server', 'host')
SERVER_PORT = config.getint('server', 'port')

WATCH_FOLDER = _get_path('paths', 'watch_folder')
PUBLIC_FOLDER = _get_path('paths', 'public_folder')
POPPLER_PATH = _get_path("paths", 'poppler_path')

CHECK_INTERVAL = config.getint('settings', 'check_interval')
MAX_RETRIES = config.getint('settings', 'max_retries')
RETRY_INTERVAL = config.getint('settings', 'retry_interval')
