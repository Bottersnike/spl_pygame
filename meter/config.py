import os

import ruamel.yaml as yaml

CONFIG_PATH = 'meter/config/config.yml'
DEFAULT_CONFIG = 'meter/config/.default_config.yml'


def load_config():
    """Load the config or create it if it doesn't exist."""
    new = False
    if not os.path.exists(CONFIG_PATH):
        with open(DEFAULT_CONFIG) as file1:
            with open(CONFIG_PATH, 'w') as file2:
                file2.write(file1.read())
        new = True

    with open(DEFAULT_CONFIG) as file_:
        default_config = yaml.safe_load(file_)
    with open(CONFIG_PATH) as file_:
        config = yaml.safe_load(file_)

    # Restore omitted values from config
    for key in default_config:
        if key not in config:
            config[key] = default_config[key]

    return config, new


if __name__ == '__main__':
    load_config()
