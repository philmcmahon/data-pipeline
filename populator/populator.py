import argparse
import json

import boto3

from populator.supported_extensions import is_supported_key

DEFAULT_BUCKET = "dh26-data-pipeline-data"


def list_s3_objects(bucket, path):
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=bucket, Prefix=path):
        for obj in page.get("Contents", []):
            yield obj["Key"]

def get_files_to_process(bucket, path):
    keys = list(list_s3_objects(bucket, path))
    supported_keys = [key for key in keys if is_supported_key(key)]
    return supported_keys


def publish_to_queue(queue_url, messages):
    sqs = boto3.client("sqs")

    for message in messages:
        sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message))


def main():
    # Process command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("queue_url", help="SQS queue URL")
    parser.add_argument("path", help="S3 key path to list objects from")
    parser.add_argument(
        "job_type",
        choices=["transcribe", "ocr", "prompt"],
        help="Type of job to run on each file",
    )
    parser.add_argument("--bucket", default=DEFAULT_BUCKET, help="S3 bucket name")
    parser.add_argument(
        "--system-prompt-file",
        help="Path to a file containing the system prompt (required for 'prompt' job type)",
    )
    args = parser.parse_args()

    if args.job_type == "prompt" and not args.system_prompt_file:
        parser.error("--system-prompt-file is required when job_type is 'prompt'")

    # If a system prompt file has been specified, read it into a variable
    system_prompt = None
    if args.system_prompt_file:
        with open(args.system_prompt_file) as f:
            system_prompt = f.read()

    # Get the list of files from the S3 bucket that we want to work on
    files_to_process = get_files_to_process(args.bucket, args.path)

    # Prepare messages containing the work we want to do
    messages = []
    for key in files_to_process:
        msg = {"bucket": args.bucket, "key": key, "jobType": args.job_type}
        if system_prompt is not None:
            msg["systemPrompt"] = system_prompt
        messages.append(msg)

    publish_to_queue(args.queue_url, messages)


    print(f"Published {len(messages)} messages to SQS queue '{args.queue_url}'")


if __name__ == "__main__":
    main()