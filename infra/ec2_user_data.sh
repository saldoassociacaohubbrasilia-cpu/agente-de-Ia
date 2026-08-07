#!/bin/bash
# Script de inicialização da instância EC2 — cole isso no campo "User data"
# na hora de criar a instância (Advanced details > User data).
# Escrito pensando na AMI padrão do free tier: Amazon Linux 2023.
#
# O que ele faz: instala Docker e sobe o Qdrant (banco vetorial) como
# container, com os dados persistidos em disco (sobrevive a reboot) e
# protegido por API key.

dnf update -y
dnf install -y docker
systemctl enable --now docker

mkdir -p /home/ec2-user/qdrant_storage
chown ec2-user:ec2-user /home/ec2-user/qdrant_storage

# TROQUE essa chave por uma senha forte ANTES de lançar a instância — é o
# que protege seu banco vetorial, já que ele vai ficar acessível pela
# internet (o Render, no plano gratuito, não tem IP fixo pra restringir por
# Security Group). Guarde essa mesma chave no QDRANT_API_KEY do seu .env.
QDRANT_API_KEY="TROQUE_ESSA_CHAVE_POR_UMA_SENHA_FORTE"

docker run -d \
  --name qdrant \
  --restart unless-stopped \
  -p 6333:6333 \
  -v /home/ec2-user/qdrant_storage:/qdrant/storage \
  -e QDRANT__SERVICE__API_KEY="${QDRANT_API_KEY}" \
  qdrant/qdrant
