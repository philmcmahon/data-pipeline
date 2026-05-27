
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

# Policy to make it easier to login to the workers
resource "aws_iam_role_policy_attachment" "workers_ssm_core" {
  role       = aws_iam_role.workers.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}
