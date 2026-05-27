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
}

#### PROJECT NAME #######
# Change this!
variable "projectName" {
  type    = string
  default = "phil-test"
}

######  QUEUES ########
# We create two quueues - a work queue and a dead letter queue. Any messages that fail to process after 3 attempts
# will be moved to the dead letter queue so they don't prevent other tasks being picked up.

resource "aws_sqs_queue" "dead_letter" {
  name = "${var.projectName}-dead-letter-queue"
}

resource "aws_sqs_queue" "work" {
  name = "${var.projectName}-queue"

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dead_letter.arn
    maxReceiveCount     = 3
  })
}

###### Output bucket #######
# Output data from the worker will be saved here

resource "aws_s3_bucket" "output" {
  bucket = "${var.projectName}-output"
}


##### Subnets, security group, key pair, role, instance profile #######
# Out of scope for this workshop. These set up the networking configuration that allows 
# the workers to access the internet, and you to access the workers via SSH.

data "aws_subnets" "vpc" {
  filter {
    name   = "vpc-id"
    values = ["vpc-0e766c22eaa6f8c08"]
  }
}

resource "aws_security_group" "workers" {
  name   = "${var.projectName}-workers-sg"
  vpc_id = "vpc-0e766c22eaa6f8c08"

# SSH access - not needed in AWS
#   ingress {
#     from_port   = 22
#     to_port     = 22
#     protocol    = "tcp"
#     cidr_blocks = ["0.0.0.0/0"]
#   }

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_iam_role" "workers" {
  name = "${var.projectName}-workers-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_instance_profile" "workers" {
  name = "${var.projectName}-workers-instance-profile"
  role = aws_iam_role.workers.name
}

#### IAM POLICIES ######
# IAM policies define which AWS resources the workers are allowed to access


# Permissions to allow the worker to access the data in the input/output buckets
resource "aws_iam_role_policy" "workers_s3" {
  name = "${var.projectName}-workers-s3-access"
  role = aws_iam_role.workers.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Effect = "Allow"
        Resource = [
          "arn:aws:s3:::dh26-data-pipeline-data/*",
          "arn:aws:s3:::dh26-data-pipeline-data",
        ]
      },
      {
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl",
          "s3:GetObject",
        ]
        Effect = "Allow"
        Resource = [
          aws_s3_bucket.output.arn,
          "${aws_s3_bucket.output.arn}/*"
        ]
      }
    ]
  })
}

# Permissions to read/write/delete messages from the queue created above
resource "aws_iam_role_policy" "workers_sqs" {
  name = "${var.projectName}-workers-sqs-access"
  role = aws_iam_role.workers.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Effect = "Allow"
        Resource = aws_sqs_queue.work.arn
      },
      {
        Action = [
          "sqs:SendMessage"
        ]
        Effect = "Allow"
        Resource = aws_sqs_queue.dead_letter.arn
      }
    ]
  })
}

# Policy to make it easier to login to the workers
resource "aws_iam_role_policy_attachment" "workers_ssm_core" {
  role       = aws_iam_role.workers.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}


# The launch template defines what type of workers we want and what they should do on startup.

# The image_id determines the operating system installed on the workers. In this case we're using the AWS Deep Learning AMI
# to save time installing GPU drivers (https://docs.aws.amazon.com/dlami/latest/devguide/overview-base.html)

# The instance_type determines the hardware (and cost per second) of the machine we want to run. In this case we're using
# the cheapest GPU instance provided by amazon, which has 16GB of video memory

# The user_data is the script we want to run when we startup the machine. See worker/setup.sh
resource "aws_launch_template" "workers" {
  name_prefix   = "${var.projectName}-workers-"
  image_id      = "ami-0630945e30e7f21a6"
  instance_type = "g4dn.xlarge" # Roughly $0.50/hour
  user_data = base64encode(<<-EOT
#!/usr/bin/env bash
set -euo pipefail

WORKING_DIRECTORY="/opt/dlami/nvme"

mkdir -p "$${WORKING_DIRECTORY}/.cache/uv" "$${WORKING_DIRECTORY}/.cache/huggingface" "$${WORKING_DIRECTORY}/tmp"

apt update
apt install -y ffmpeg libavcodec-dev libavformat-dev libavutil-dev libswresample-dev libswscale-dev

git clone https://github.com/philmcmahon/data-pipeline.git $${WORKING_DIRECTORY}
chown -R "ubuntu:ubuntu" $${WORKING_DIRECTORY}

bash $${WORKING_DIRECTORY}/worker/initialise-worker.sh '${aws_sqs_queue.work.url}' '${aws_s3_bucket.output.bucket}' $${WORKING_DIRECTORY}

EOT
  )

  network_interfaces {
    security_groups             = [aws_security_group.workers.id]
  }

  iam_instance_profile {
    name = aws_iam_instance_profile.workers.name
  }
}

# In the auto scaling group we define how many workers we want
resource "aws_autoscaling_group" "workers" {
  name                = "${var.projectName}-workers-asg"
  min_size            = 0
  max_size            = 5
  vpc_zone_identifier = data.aws_subnets.vpc.ids

  launch_template {
    id      = aws_launch_template.workers.id
    version = "$Latest"
  }
}

# Safety measure - workers will not stop by themselves - this ensures all workers are
# switched off at 11pm to save money/energy.
resource "aws_autoscaling_schedule" "scale_down_evening" {
  scheduled_action_name  = "${var.projectName}-scale-down-evening"
  autoscaling_group_name = aws_autoscaling_group.workers.name
  min_size               = 0
  max_size               = 0
  desired_capacity       = 0
  recurrence             = "0 23 * * *"
}
