import argparse
import json
import os

import boto3
import pika

import whisperx
import gc
from whisperx.diarize import DiarizationPipeline


# whisper settings
device = "cuda"
batch_size = 8 # reduce if low on GPU mem
compute_type = "float16" # change to "int8" if low on GPU mem (may reduce accuracy)

model = whisperx.load_model("large-v2", device, compute_type=compute_type)

def transcribe_audio(file_path):
    # Transcribe file with whisperx
    result = model.transcribe(file_path, batch_size=batch_size)

    # write vtt output to file
    vtt_path = file_path + ".vtt"
    with open(vtt_path, "w") as vtt_file:
        vtt_file.write(result["vtt"])
    print(f"Transcription complete. VTT file saved to: {vtt_path}")


def consume_queue(queue_name, url):
    s3 = boto3.client("s3")
    connection = pika.BlockingConnection(pika.URLParameters(url))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)

    while True:
        method, properties, body = channel.basic_get(queue=queue_name, auto_ack=False)
        if method is None:
            break

        message = json.loads(body)
        bucket = message["bucket"]
        key = message["key"]
        local_path = os.path.join("/tmp", os.path.basename(key))

        s3.download_file(bucket, key, local_path)
        print(f"Downloaded: {local_path}")
        transcribe_audio(local_path)
        os.remove(local_path)

        channel.basic_ack(delivery_tag=method.delivery_tag)

    connection.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("queue_name", help="RabbitMQ queue name")
    args = parser.parse_args()

    rabbitmq_password = os.environ.get("QUEUE_PASSWORD")
    if not rabbitmq_password:
        print("Error: QUEUE_PASSWORD environment variable is not set")
        return

    rabbitmq_url = f"amqp://dataharvest:{rabbitmq_password}@rabbitmq.dh24workshop.uk"

    consume_queue(args.queue_name, rabbitmq_url)


if __name__ == "__main__":
    main()
