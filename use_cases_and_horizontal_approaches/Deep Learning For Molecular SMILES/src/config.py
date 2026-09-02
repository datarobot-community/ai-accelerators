import yaml


def load_config(path_or_dict):
    """Load configuration from a YAML file path or return a dict directly."""
    if isinstance(path_or_dict, dict):
        return path_or_dict
    with open(path_or_dict) as f:
        return yaml.safe_load(f)
