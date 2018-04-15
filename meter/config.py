import os

import ruamel.yaml as yaml


CONFIG_PATH = 'meter/config/config.yml'
DEFAULT_CONFIG = 'meter/config/.default_config.yml'


def load_config():
    new = False
    if not os.path.exists(CONFIG_PATH):
        with open(DEFAULT_CONFIG) as file1:
            with open(CONFIG_PATH, 'w') as file2:
                file2.write(file1.read())
        new = True

    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    return config, new


if __name__ == '__main__':
    load_config()
