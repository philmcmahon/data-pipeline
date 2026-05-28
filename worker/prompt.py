import os

import jinja2

from vllm import start_vllm_server, VLLM_BASE_URL

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")

_openai_client = None


def get_user_prompt(file_name, s3_uri, file_content):
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(PROMPTS_DIR),
        autoescape=False,
    )
    template = env.get_template("user_prompt.j2")
    return template.render(file_name=file_name, s3_uri=s3_uri, file_content=file_content)


def get_openai_client():
    global _openai_client
    if _openai_client is None:
        start_vllm_server("Qwen/Qwen3-4B", [
            "--max-model-len", "16384",
            "--gpu-memory-utilization", "0.9",
        ])
        from openai import OpenAI
        _openai_client = OpenAI(base_url=f"{VLLM_BASE_URL}/v1", api_key="unused")
    return _openai_client


def run_prompt(file_path, s3_uri, system_prompt):
    client = get_openai_client()
    print(f"Running prompt on file: {file_path}")
    with open(file_path) as f:
        file_content = f.read()

    response = client.chat.completions.create(
        model="Qwen/Qwen3-4B",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": get_user_prompt(os.path.basename(file_path), s3_uri, file_content)},
        ],
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    json_path = file_path + ".json"
    with open(json_path, "w") as f:
        f.write(response.choices[0].message.content)
    print(f"Prompt complete: {json_path}")
    return json_path
