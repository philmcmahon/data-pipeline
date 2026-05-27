terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      version = "6.45.0"
    }
  }
}

provider "aws" {
  region = "eu-west-1"
}


resource "aws_s3_bucket" "source_data" {
  bucket = "dh26-data-pipeline-data"
}

# resource "aws_s3_bucket" "configuration" {
#   bucket = "dh26-data-pipeline-config"
# }
