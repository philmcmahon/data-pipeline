import argparse
import json
import os
import sys
import time

# Ensure all print output is flushed immediately
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

import boto3

from worker.ocr import ocr_document
from worker.prompt import run_prompt
from worker.transcribe import transcribe_audio

AWS_REGION = "eu-west-1"
WORK_DIR = os.environ.get("WORK_DIR", "/tmp")

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
            s3_key = f"prompt/{os.path.splitext(original_filename)[0]}.json"
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
