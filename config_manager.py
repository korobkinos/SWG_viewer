import json

def save_config(file_path, config_data):
    with open(file_path, 'w') as f:
        json.dump(config_data, f, indent=4)


def load_config(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)