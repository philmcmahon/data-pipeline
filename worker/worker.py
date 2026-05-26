import argparse
import json
import os
import sys

import boto3

import whisperx
from whisperx.diarize import DiarizationPipeline
from worker.detect_filetype import detect_file_type

from docling.document_converter import DocumentConverter

AWS_REGION = "eu-west-1"


def configure_output_streams():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True, write_through=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(line_buffering=True, write_through=True)

def initialize_whisperx():
    # whisper settings
    device = "cuda"
    batch_size = 8 # reduce if low on GPU mem
    compute_type = "float16" # change to "int8" if low on GPU mem (may reduce accuracy)

    model = whisperx.load_model("large-v2", device, compute_type=compute_type)
    return model

def initialize_document_converter():
    converter = DocumentConverter()
    return converter

def ocr_document(file_path, document_converter):
    # Convert document to text with docling
    result = document_converter.convert(file_path)
    markdown = result.document.export_to_markdown()
    txt_path = file_path + ".txt"
    with open(txt_path, "w") as txt_file:
        txt_file.write(markdown)
    print(f"OCR complete. Text file saved to: {txt_path}")
    return txt_path

def transcribe_audio(file_path, whisperx_model, batch_size=8):
    # Transcribe file with whisperx
    result = whisperx_model.transcribe(file_path, batch_size=batch_size)

    # write vtt output to file
    vtt_path = file_path + ".vtt"
    with open(vtt_path, "w") as vtt_file:
        vtt_file.write(result["vtt"])
    print(f"Transcription complete. VTT file saved to: {vtt_path}")
    return vtt_path


def consume_queue(queue_url, whisperx_model, document_converter):
    s3 = boto3.client("s3", region_name=AWS_REGION)
    sqs = boto3.client("sqs", region_name=AWS_REGION)

    while True:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=10,
        )

        messages = response.get("Messages", [])
        if not messages:
            break

        sqs_message = messages[0]
        message = json.loads(sqs_message["Body"])
        bucket = message["bucket"]
        key = message["key"]
        local_path = os.path.join("/tmp", os.path.basename(key))

        s3.download_file(bucket, key, local_path)
        print(f"Downloaded: {local_path}")
        file_type = detect_file_type(local_path)
        if file_type == "audio_video":
            transcript_path = transcribe_audio(local_path, whisperx_model)
        elif file_type in ["PDF"]:
            ocr_path = ocr_document(local_path, document_converter)
        else:
            print(f"Unsupported file type for file: {local_path}")

        os.remove(local_path)

        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=sqs_message["ReceiptHandle"],
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("queue_url", help="SQS queue URL")
    args = parser.parse_args()

    configure_output_streams()

    whisperx_model = initialize_whisperx()
    document_converter = initialize_document_converter()

    consume_queue(args.queue_url, whisperx_model, document_converter)


if __name__ == "__main__":
    main()
