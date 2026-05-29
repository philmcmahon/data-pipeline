import argparse
import csv
import json
import sys

import boto3


def main():
    parser = argparse.ArgumentParser(description="Collect JSON results from S3 and write to CSV")
    parser.add_argument("bucket", help="S3 bucket name")
    parser.add_argument("path", help="S3 path prefix to fetch files from")
    parser.add_argument("-o", "--output", default="output.csv", help="Output CSV file (default: output.csv)")
    args = parser.parse_args()

    session = boto3.Session(profile_name="dataharvest")
    s3 = session.client("s3")
    prefix = args.path.strip("/") + "/"

    paginator = s3.get_paginator("list_objects_v2")
    records = []

    for page in paginator.paginate(Bucket=args.bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/"):
                continue
            response = s3.get_object(Bucket=args.bucket, Key=key)
            body = response["Body"].read()
            if not body:
                print(f"Skipping empty file: s3://{args.bucket}/{key}", file=sys.stderr)
                continue
            print(body)
            data = json.loads(body)
            records.append(data)

    if not records:
        print(f"No files found under s3://{args.bucket}/{prefix}", file=sys.stderr)
        sys.exit(1)

    fieldnames = ["relevant", "quotes", "notes"]
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({
                "relevant": record.get("relevant"),
                "quotes": json.dumps(record.get("quotes", [])),
                "notes": record.get("notes", ""),
            })

    print(f"Wrote {len(records)} records to {args.output}")


if __name__ == "__main__":
    main()
