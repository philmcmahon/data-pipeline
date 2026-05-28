
data "aws_subnets" "vpc" {
  filter {
    name   = "vpc-id"
    values = ["vpc-0e766c22eaa6f8c08"]
  }
}

resource "aws_key_pair" "rabbitmq" {
  key_name   = "rabbitmq-key"
  public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDl+F8DyelJoazAzh7P4l1i1ACD3eppyZ/7l65/2Sp+aE41+EV0F8VV8XYaUs2qV25OPIdWheVKZkP/JL/1dxtlN5SzuhEq/DMEIOJP5Mo5ot6GkSoevCSnlcg06vIChXmAC7DL8cedUcGajL4WrO+r7vaV8IlBLGACG5y0tibyoII6aauLHgndcKZmWOTOzL4jrbjiTMwhs+CgC9v6fHOSTxhf59+YJ+getUql6XinefmcAoihEQcdtDX8JY+bN/YwXza1joiktmrHsxZVDcF07sMEqBLiMR+yN3nkSXpgUSbGGqU/Yrf6NYucCQd/YnTOap62JnbD5sJxMX6GyP3y7ESSPHLI3Wqsve8DuhfmeI3kqo2Eq/+vYTntU/WivDErP90XZZ9FO7ZKbDuXVZlGxKdh6HkmwJ4Ipkmliec9EDYDNFjGhd6et9YpeTuVGYnfkC4PbFMQ2RvtQdmU0sSZLzFJrRkrHx5T6o+LfUZLC1yM4Ms2Uml0hdaxGp+wCoM= philip_mcmahon@31814.gnm.int"
}

resource "aws_security_group" "rabbitmq" {
  name   = "rabbitmq-sg"
  vpc_id = "vpc-0e766c22eaa6f8c08"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 15672
    to_port     = 15672
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

    ingress {
    from_port   = 5672
    to_port     = 5672
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_iam_role" "rabbitmq" {
  name = "rabbitmq-role"

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

resource "aws_iam_role_policy" "rabbitmq_s3_read" {
  name = "rabbitmq-s3-read"
  role = aws_iam_role.rabbitmq.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = [
        "s3:GetObject",
        "s3:ListBucket"
      ]
      Effect = "Allow"
      Resource = [
        aws_s3_bucket.source_data.arn,
        "${aws_s3_bucket.source_data.arn}/*",
        aws_s3_bucket.configuration.arn,
        "${aws_s3_bucket.configuration.arn}/*"
      ]
    }]
  })
}

resource "aws_iam_instance_profile" "rabbitmq" {
  name = "rabbitmq-instance-profile"
  role = aws_iam_role.rabbitmq.name
}

resource "aws_launch_template" "rabbitmq" {
  name_prefix   = "rabbitmq-"
  image_id      = "ami-07dcad2e028cc44c9"
  instance_type = "t3.small"
  key_name      = aws_key_pair.rabbitmq.key_name

user_data = base64encode(file("${path.module}/../rabbitmq/setup.sh"))


  network_interfaces {
    associate_public_ip_address = true
    security_groups             = [aws_security_group.rabbitmq.id]
  }

  iam_instance_profile {
    name = aws_iam_instance_profile.rabbitmq.name
  }
}

resource "aws_autoscaling_group" "rabbitmq" {
  name                = "rabbitmq-asg"
  desired_capacity    = 1
  max_size            = 1
  min_size            = 1
  vpc_zone_identifier = data.aws_subnets.vpc.ids

  launch_template {
    id      = aws_launch_template.rabbitmq.id
    version = "$Latest"
  }
}

