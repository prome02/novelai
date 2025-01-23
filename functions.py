import json
from pathlib import Path

import json5
import yaml
from jinja2 import Environment
from openai import OpenAI

from config import getconfig

debug = getconfig("NOVELAI_DEBUG")

def init_client():
    client = OpenAI(
        base_url=getconfig("OPENAI_API_BASE"),
        api_key=getconfig("OPENAI_API_KEY")
    )
    return client

def call_ai_simple(client, request, messages=None, stopAtSectionBlock=[]):
    if debug:
        print(request)

    messagesToUse = [
        {"role": "system",
         "content": "You are a helpful, smart, kind, and efficient AI assistant. You always fulfill the user's requests to the best of your ability. "},
        {"role": "user", "content": str(request)},
        {"role": "assistant", "content": "Response:"}
    ] if messages is None else messages

    completion = client.chat.completions.create(
        model=getconfig("OPENAI_API_MODEL"),
        messages=messagesToUse,
        temperature=0.8,
        stream=True,
        # max_tokens=3000
    )

    try:
        response = ""
        for chunk in completion:
            chunktxt = str(chunk.choices[0].delta.content or '')

            if chunktxt.strip() in stopAtSectionBlock:
                if debug:
                    print("ENCOUNTERED SECTION BLOCK - STOPPING!")
                break

            response += chunktxt
            if debug:
                print(chunktxt, end="")
                #print(chunktxt)
    finally:
        completion.close()

    return response

def get_template(template_name):
    novel_ai_templates_directories = getconfig("NOVELAI_TEMPLATES_DIR").split(",")
    for directory in novel_ai_templates_directories:
        jinja_filename = directory + "/" + template_name + ".jinja2"
        if Path(jinja_filename).is_file():
            return readfile(jinja_filename)
    raise ValueError("Invalid template name - " + template_name + ".jinja2 not found in " + str(novel_ai_templates_directories))

def call_ai_with_template(client, template_name, metadata, stop_at_section_block=[]):
    novel_step_templates = get_template(template_name).split("<|endstep|>")

    # store responses in multi-step processes
    responses = []
    metadata.update({
        "responses": responses
    })

    # run each step (if only one, will only run first step and return)
    for stepIndex, stepTemplate in enumerate(novel_step_templates):
        jinja_env = Environment(extensions=['jinja2.ext.do'])
        jinja_env.policies['json.dumps_kwargs']['ensure_ascii'] = False
        jinja_env.policies['json.dumps_kwargs']['sort_keys'] = False
        jinja_template = jinja_env.from_string(stepTemplate)
        output = jinja_template.render(metadata)

        messages = None
        if output.find("<|eot_id|>") != -1 or output.find("<|start_header_id|>") != -1:
            messages = []
            messages_parts = output.split("<|eot_id|>")
            for part in messages_parts:
                role = get_substring_between(part, "<|start_header_id|>", "<|end_header_id|>")
                if role:
                    content = part.replace("<|start_header_id|>{}<|end_header_id|>".format(role), "").strip()
                    messages.append({
                        "role": role,
                        "content": content
                    })
                    if role == "output":
                        if debug:
                            print("Encountered output block")
                            print(content)
                        return content
                else:
                    print("ERROR: Skipping template part because missing <|start_header_id|><|end_header_id|>")

        # CALL AI!
        response = call_ai_simple(client, output, messages, stop_at_section_block)
        json_data = None
        try:
            if stepIndex < len(novel_step_templates) - 1:  # don't bother parsing json of last step
                raw_json = extract_json(response)
                if raw_json is not None and raw_json[0] in ["{", "[", "\""]: # might be json, so lets try to clean it if syntax is invalid
                    json_data = json5.loads(clean_json(client, raw_json)) # note: if clean_json fails, it throws exception and json_data will just be None
        except Exception as e:
            if debug:
                print("ERROR: Could not extract JSON data from step " + str(stepIndex))
                print(e)
            #raise e

        finally: # always append to responses list
            responses.append({
                "text": response,
                "data": json_data
            })

    return responses[-1]["text"]

def rindex(lst, value):
    return len(lst) - lst[::-1].index(value) - 1

def get_substring_between(text, start, end):
    try:
        start_index = text.index(start) + len(start)
        end_index = text.index(end, start_index)
        end_index2 = text.rfind(end, start_index)
        if end_index2 > end_index:  # find between last one, if at all possible
            return text[start_index:end_index2]
        else:
            return text[start_index:end_index]
    except ValueError:
        return None  # Return an empty string if the delimiters are not found

def clean_json(client, rawJson):
    try:
        if debug:
            print("RAW JSON TO CLEAN: " + rawJson)
        loaded = json.loads(rawJson, strict=False)
        if debug:
            print("Loaded using standard json library")
        return json.dumps(loaded, indent=2, sort_keys=False)
    except Exception as e:
        if debug:
            print(e)
        try:
            loaded = json5.loads(rawJson, strict=False)
            if debug:
                print("Loaded using json5 library")
            return json5.dumps(loaded, sort_keys=False, indent=2)
        except ValueError as e: # invalid! clean it!!!
            if debug:
              print(e)
            cleanedJson = extract_json(call_ai_with_template(client, "cleanjson", { "rawJson": rawJson }, ['```', '``', '`']))
            loaded = json5.loads(cleanedJson) # validate format
            return json5.dumps(loaded)

def clean_yaml(client, rawYaml):
    try:
        data = yaml.safe_load(rawYaml) # validate format!
        return rawYaml
    except Exception as e: # invalid! clean it!!!
        cleanedYaml = extract_yaml(call_ai_with_template(client, "cleanyaml", { "rawYaml": rawYaml }, ['```', '``']))
        yaml.safe_load(cleanedYaml) # validate format!
        return cleanedYaml

def extract_json(response):
    if result := get_substring_between(response, "```json", "```"):
        return result.strip()
    if result := get_substring_between(response, "```", "```"):
        return result.strip()
    if result := get_substring_between(response, "{", "}"):
        return "{" + result + "}"
    return response

def extract_yaml(response):
    if result := get_substring_between(response, "```yaml", "```"):
        return result.strip()
    if result := get_substring_between(response, "```", "```"):
        return result.strip()
    if result := get_substring_between(response, "{", "}"):
        return "{" + result + "}"
    return response

def readfile(filename):
    with open(filename, 'r', encoding='utf-8', errors='ignore') as file:
        data = file.read()
        return data

def writefile(filename, contents):
    with open(filename, "w") as text_file:
        print(contents, file=text_file, end="")