import argparse
import json
import os

import boto3
import pika

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
