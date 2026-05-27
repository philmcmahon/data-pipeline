import argparse
import json
import os
import subprocess
import time

import boto3
import requests

AWS_REGION = "eu-west-1"
VLLM_BASE_URL = "http://127.0.0.1:8000"
WORK_DIR = os.environ.get("WORK_DIR", "/tmp")

_whisperx_model = None
_document_converter = None
_vllm_process = None
_openai_client = None

SYSTEM_PROMPT = (
    "You are an investigative journalist. Your job is to identify sections of the "
    "file which match the user prompt. The output should be in CSV format, with 1 row "
    "per match. Each row should have the format "
    "input_file_name,input_file_s3_uri,matching_text,first_line,second_line"
)


def get_user_prompt(file_name, s3_uri, document):
    return (
        "You will see a document.\n"
        "\n"
        "You should identify whether this document is relevant to the investigation, and write some\n"
        "short notes describing why it is or is not relevant.\n"
        "\n"
        "Your output should be a CSV following the schema:\n"
        "\n"
        '"input_file_name,input_file_s3_uri,matching_text,line_number_of_matching_text"\n'
        "\n"
        "For example:\n"
        '"file.txt,s3://bucket//file.txt,matching_text,1"\n'
        "\n"
        "The output *must* be parseable as JSON. Do not add any text before or after the JSON.\n"
        "Here is the document:\n"
        "<document>\n"
        f"<file_name>{file_name}</file_name>\n"
        f"<s3_uri>{s3_uri}</s3_uri>\n"
        f"<contents>{document}</contents>\n"
        "</document>"
    )


def start_vllm_server(model, extra_args=None):
    global _vllm_process
    cmd = ["vllm", "serve", model, "--host", "127.0.0.1", "--port", "8000"]
    if extra_args:
        cmd.extend(extra_args)
    print(f"Starting vllm server: {' '.join(cmd)}")
    _vllm_process = subprocess.Popen(cmd)

    # Wait for server to be ready
    for _ in range(120):
        try:
            r = requests.get(f"{VLLM_BASE_URL}/v1/models", timeout=2)
            if r.status_code == 200:
                print("vllm server is ready")
                return
        except requests.ConnectionError:
            pass
        time.sleep(5)
    raise RuntimeError("vllm server failed to start within timeout")


def get_whisperx_model():
    global _whisperx_model
    if _whisperx_model is None:
        import whisperx
        _whisperx_model = whisperx.load_model(
            "medium", "cuda", compute_type="float16"
        )
    return _whisperx_model


def get_document_converter():
    global _document_converter
    if _document_converter is None:
        start_vllm_server("ibm-granite/granite-docling-258M", [
            "--max-num-seqs", "512",
            "--max-num-batched-tokens", "8192",
            "--enable-chunked-prefill",
            "--gpu-memory-utilization", "0.9",
        ])
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import VlmConvertOptions, VlmPipelineOptions
        from docling.datamodel.vlm_engine_options import ApiVlmEngineOptions, VlmEngineType
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.pipeline.vlm_pipeline import VlmPipeline

        vlm_options = VlmConvertOptions.from_preset(
            "granite_docling",
            engine_options=ApiVlmEngineOptions(
                runtime_type=VlmEngineType.API,
                url=f"{VLLM_BASE_URL}/v1/chat/completions",
                params={
                    "model": "ibm-granite/granite-docling-258M",
                    "temperature": 0.0,
                    "max_tokens": 4096,
                    "skip_special_tokens": False,
                },
                timeout=90,
            ),
        )
        pipeline_options = VlmPipelineOptions(
            vlm_options=vlm_options, enable_remote_services=True
        )
        _document_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options, pipeline_cls=VlmPipeline
                )
            }
        )
    return _document_converter


def get_openai_client():
    global _openai_client
    if _openai_client is None:
        start_vllm_server("Qwen/Qwen3-8B-Q4_K_M")
        from openai import OpenAI
        _openai_client = OpenAI(base_url=f"{VLLM_BASE_URL}/v1", api_key="unused")
    return _openai_client


def transcribe_audio(file_path):
    model = get_whisperx_model()
    print(f"Transcribing audio file: {file_path}")
    # You can remove the task parameter here to prevent translation to english
    result = model.transcribe(file_path, batch_size=8, task="translate")
    result_text = ("\n".join(seg["text"] for seg in result["segments"]))
    txt_path = file_path + ".txt"
    with open(txt_path, "w") as f:
        f.write(result_text)
    print(f"Transcription complete: {txt_path}")
    return txt_path


def ocr_document(file_path):
    converter = get_document_converter()
    print(f"Performing OCR on document: {file_path}")
    result = converter.convert(file_path)
    md_path = file_path + ".md"
    with open(md_path, "w") as f:
        f.write(result.document.export_to_markdown())
    print(f"OCR complete: {md_path}")
    return md_path


def run_prompt(file_path, s3_uri, system_prompt):
    client = get_openai_client()
    print(f"Running prompt on file: {file_path}")
    with open(file_path) as f:
        file_content = f.read()

    response = client.chat.completions.create(
        model="Qwen/Qwen3-8B-Q4_K_M",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": get_user_prompt(os.path.basename(file_path), s3_uri, file_content)},
        ],
    )
    csv_path = file_path + ".csv"
    with open(csv_path, "w") as f:
        f.write(response.choices[0].message.content)
    print(f"Prompt complete: {csv_path}")
    return csv_path


def upload_to_s3(s3_client, local_path, bucket, s3_key):
    s3_client.upload_file(local_path, bucket, s3_key)
    print(f"Uploaded to s3://{bucket}/{s3_key}")


def consume_queue(queue_url, output_bucket):
    s3 = boto3.client("s3", region_name=AWS_REGION)
    sqs = boto3.client("sqs", region_name=AWS_REGION)

    while True:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=10,
            # Allow 15 minutes for message to timeout
            VisibilityTimeout=15 * 60
        )

        messages = response.get("Messages", [])
        if not messages:
            print("No messages in queue, waiting...")
            # sleep
            time.sleep(5)
            continue

        sqs_message = messages[0]
        message = json.loads(sqs_message["Body"])
        bucket = message["bucket"]
        key = message["key"]
        job_type = message["jobType"]
        original_filename = os.path.basename(key)
        os.makedirs(WORK_DIR, exist_ok=True)
        local_path = os.path.join(WORK_DIR, original_filename)

        s3.download_file(bucket, key, local_path)
        print(f"Downloaded: {local_path}")

        if job_type == "transcribe":
            output_path = transcribe_audio(local_path)
            s3_key = f"transcript/{os.path.splitext(original_filename)[0]}.txt"
            upload_to_s3(s3, output_path, output_bucket, s3_key)
            os.remove(output_path)
        elif job_type == "ocr":
            output_path = ocr_document(local_path)
            s3_key = f"ocr/{os.path.splitext(original_filename)[0]}.md"
            upload_to_s3(s3, output_path, output_bucket, s3_key)
            os.remove(output_path)
        elif job_type == "prompt":
            s3_uri = f"s3://{bucket}/{key}"
            output_path = run_prompt(local_path, s3_uri, message["systemPrompt"])
            s3_key = f"prompt/{os.path.splitext(original_filename)[0]}.csv"
            upload_to_s3(s3, output_path, output_bucket, s3_key)
            os.remove(output_path)

        os.remove(local_path)

        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=sqs_message["ReceiptHandle"],
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("queue_url", help="SQS queue URL")
    parser.add_argument("output_bucket", help="S3 bucket for output files")
    args = parser.parse_args()

    consume_queue(args.queue_url, args.output_bucket)


if __name__ == "__main__":
    main()
