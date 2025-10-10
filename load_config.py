import os
import json
import re
from dotenv import load_dotenv


def load_config_with_env_vars(config_path):
    """
    Loads config.json and replaces any ${VAR_NAME} with the value from environment variables.
    """
    load_dotenv()
    with open(config_path, 'r') as f:
        config_str = f.read()

    # Replace ${VAR_NAME} with os.environ[VAR_NAME]
    def replacer(match):
        var_name = match.group(1)
        value = os.getenv(var_name)
        if value is None:
            # Don't raise; log a warning and substitute an empty string so callers can handle missing values
            print(f"Warning: Environment variable '{var_name}' not set but referenced in config.json")
            return ""
        return value

    config_str = re.sub(r'\$\{([A-Z0-9_]+)\}', replacer, config_str)
    return json.loads(config_str)

if __name__ == "__main__":
    config = load_config_with_env_vars("config.json")
    print(json.dumps(config, indent=2))
