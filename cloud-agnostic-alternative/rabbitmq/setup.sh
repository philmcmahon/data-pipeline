#!/bin/sh

apt-get install curl gnupg apt-transport-https -y

## Team RabbitMQ's signing key
curl -1sLf "https://keys.openpgp.org/vks/v1/by-fingerprint/0A9AF2115F4687BD29803A206B73A36E6026DFCA" | gpg --dearmor | tee /usr/share/keyrings/com.rabbitmq.team.gpg > /dev/null

## Add apt repositories maintained by Team RabbitMQ
tee /etc/apt/sources.list.d/rabbitmq.list <<EOF
## Modern Erlang/OTP releases
##
deb [arch=amd64 signed-by=/usr/share/keyrings/com.rabbitmq.team.gpg] https://deb1.rabbitmq.com/rabbitmq-erlang/ubuntu/noble noble main
deb [arch=amd64 signed-by=/usr/share/keyrings/com.rabbitmq.team.gpg] https://deb2.rabbitmq.com/rabbitmq-erlang/ubuntu/noble noble main

## Latest RabbitMQ releases
##
deb [arch=amd64 signed-by=/usr/share/keyrings/com.rabbitmq.team.gpg] https://deb1.rabbitmq.com/rabbitmq-server/ubuntu/noble noble main
deb [arch=amd64 signed-by=/usr/share/keyrings/com.rabbitmq.team.gpg] https://deb2.rabbitmq.com/rabbitmq-server/ubuntu/noble noble main
EOF

## Update package indices
apt-get update -y

## Install Erlang packages
apt-get install -y erlang-base \
                        erlang-asn1 erlang-crypto erlang-eldap erlang-ftp erlang-inets \
                        erlang-mnesia erlang-os-mon erlang-parsetools erlang-public-key \
                        erlang-runtime-tools erlang-snmp erlang-ssl \
                        erlang-syntax-tools erlang-tftp erlang-tools erlang-xmerl

## Install rabbitmq-server and its dependencies
apt-get install rabbitmq-server -y --fix-missing

rabbitmq-plugins enable rabbitmq_management

# Create a new RabbitMQ user
rabbitmqctl add_user admin 'CHANGE_ME_STRONG_PASSWORD'

# Set the user as an administrator
rabbitmqctl set_user_tags admin administrator

# Grant full permissions on the default vhost
rabbitmqctl set_permissions -p / admin ".*" ".*" ".*"

# Create dataharvest user with queue configure/read/write permissions
rabbitmqctl add_user dataharvest 'CHANGE_ME_STRONG_PASSWORD'
rabbitmqctl set_permissions -p / dataharvest ".*" ".*" ".*"