import json
import os

import gradio

config = {
    "RETRY_COUNT": int(os.getenv('RETRY_COUNT', '2')),
    "SERVER_PORT": int(os.getenv("SERVER_PORT", 8124)),
    "NOVELAI_DEBUG": os.getenv('NOVELAI_DEBUG', 'False') == "True",
    "OPENAI_API_BASE": os.getenv("OPENAI_API_BASE", "http://localhost:1234/v1"), # use https://api.openai.com/v2 for OPEN AI
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "lm-studio"),
    "OPENAI_API_MODEL": os.getenv("OPENAI_API_MODEL", "lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF"), # use "openai-gpt" for OPEN AAI
    "NOVELAI_TEMPLATES_DIR": os.getenv("NOVELAI_TEMPLATES_DIR", "templates")
}

def getallconfig():
    return config

def getconfig(name: str):
    return getallconfig()[name]

def updateconfig(newconfig):
    for arr in newconfig:
        config[arr[0]] = arr[1]
    return "Saved. All changes should take effect immediately except for RETRY_COUNT and SERVER_PORT. "
    #config.update(config)