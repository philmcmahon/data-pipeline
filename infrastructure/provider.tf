#### PROVIDER SETUP #######
# Out of scope for this workshop - this tells OpenTofu how to talk to AWS.
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
  profile = "dataharvest"
}
