import os
import json

def get_json_content(path):
    return json.loads(get_content(path))

def get_content(path):
    dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(dir, path)) as f:
        return f.read()
