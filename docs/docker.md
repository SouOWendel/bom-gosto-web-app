# 🐳 Guia de Arquitetura, Infraestrutura e Fluxo do Docker

Este documento descreve como o ecossistema de containers do monorepo foi planejado para a **Confeitaria Bom Gosto**, cobrindo a integração entre o **Front-End (Angular)**, **Back-End (Django REST)** e **Banco de Dados (PostgreSQL)**, além do funcionamento do Hot Reload e instruções operacionais.

---

## 📐 Visão Geral da Arquitetura

O ambiente de desenvolvimento local é totalmente isolado e orquestrado via **Docker Compose**, que gerencia 3 containers conectados em uma mesma rede virtualizada (`bridge`):

```text
               +-------------------------------------------------------+
               |                     MÁQUINA HOST                      |
               |                  (Seu Computador)                     |
               +---------------------------+---------------------------+
                                           |
                   +-----------------------+-----------------------+
                   |                                               |
         http://localhost:4200                           http://localhost:8000
                   |                                               |
                   v                                               v
     +---------------------------+                   +---------------------------+
     |     CONTAINER FRONTEND    |                   |     CONTAINER BACKEND     |
     |      (Angular / Node)     | -- HTTP (API) --> |      (Django / Python)    |
     +---------------------------+                   +---------------------------+
                                                                   |
                                                          Porta Interna 5432
                                                                   v
                                                     +---------------------------+
                                                     |    CONTAINER POSTGRES     |
                                                     |    (Banco de Dados)       |
                                                     +---------------------------+
                                                                   |
                                                            Volume Nomeado
                                                                   v
                                                     +---------------------------+
                                                     |  postgres_data (Disco)    |
                                                     +---------------------------+
