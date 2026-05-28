import argparse
import json
import os

import boto3
import pika

DEFAULT_BUCKET = "dataharvest26-pipeline-workshop-source-data"

SUPPORTED_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".odt",
    ".rtf",
    ".txt",
    ".md",
}

SUPPORTED_AUDIO_VIDEO_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".flac",
    ".ogg",
    ".wma",
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
    ".m4v",
}

SUPPORTED_EXTENSIONS = SUPPORTED_DOCUMENT_EXTENSIONS | SUPPORTED_AUDIO_VIDEO_EXTENSIONS


def is_supported_key(key):
    # Ignore folder placeholders and only allow known document/audio-video extensions.
    if key.endswith("/"):
        return False

    extension = os.path.splitext(key)[1].lower()
    return extension in SUPPORTED_EXTENSIONS


def list_s3_objects(bucket, path):
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=bucket, Prefix=path):
        for obj in page.get("Contents", []):
            yield obj["Key"]


def publish_to_queue(queue_name, messages, url):
    connection = pika.BlockingConnection(pika.URLParameters(url))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)

    for message in messages:
        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2),
        )

    connection.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("queue_name", help="RabbitMQ queue name")
    parser.add_argument("path", help="S3 key path to list objects from")
    parser.add_argument("--bucket", default=DEFAULT_BUCKET, help="S3 bucket name")
    args = parser.parse_args()

    rabbitmq_password = os.environ.get("QUEUE_PASSWORD")
    if not rabbitmq_password:
        print("Error: QUEUE_PASSWORD environment variable is not set")
        return

    rabbitmq_url = f"amqp://dataharvest:{rabbitmq_password}@rabbitmq.dh24workshop.uk"

    keys = list(list_s3_objects(args.bucket, args.path))
    supported_keys = [key for key in keys if is_supported_key(key)]
    skipped_count = len(keys) - len(supported_keys)

    messages = [{"bucket": args.bucket, "key": key} for key in supported_keys]

    publish_to_queue(args.queue_name, messages, url=rabbitmq_url)
    print(f"Published {len(messages)} messages to queue '{args.queue_name}'")
    if skipped_count:
        print(f"Skipped {skipped_count} unsupported files based on extension")


if __name__ == "__main__":
    main()