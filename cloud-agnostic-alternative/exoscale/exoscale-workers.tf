
data "exoscale_template" "ubuntu" {
  zone = "at-vie-2"
  name = "Linux Ubuntu 24.04 LTS 64-bit"
}

data "exoscale_private_network" "dataharvest" {
  zone = "at-vie-2"
  name = "dataharvest_network"
}

resource "exoscale_security_group" "workers" {
  name = "workers-sg"
}

resource "exoscale_security_group_rule" "workers_ssh" {
  security_group_id = exoscale_security_group.workers.id
  type              = "INGRESS"
  protocol          = "TCP"
  cidr              = "0.0.0.0/0"
  start_port        = 22
  end_port          = 22
}

resource "exoscale_security_group_rule" "workers_http" {
  security_group_id = exoscale_security_group.workers.id
  type              = "EGRESS"
  protocol          = "TCP"
  cidr              = "0.0.0.0/0"
  start_port        = 80
  end_port          = 80
}

resource "exoscale_security_group_rule" "workers_https" {
  security_group_id = exoscale_security_group.workers.id
  type              = "EGRESS"
  protocol          = "TCP"
  cidr              = "0.0.0.0/0"
  start_port        = 443
  end_port          = 443
}

# resource "exoscale_instance_pool" "workers" {
#   zone = "at-vie-2"
#   name = "workers"

#   template_id        = data.exoscale_template.ubuntu.id
#   instance_type      = "gpu3080ti.small"
#   disk_size          = 100
#   size               = 1
#   key_pair           = "dataharvest_key"
#   network_ids        = [data.exoscale_private_network.dataharvest.id]
#   security_group_ids = [exoscale_security_group.workers.id]
# }