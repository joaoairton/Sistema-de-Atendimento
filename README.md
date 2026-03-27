# Sistema de Atendimento v1.0

Aplicação web em **Python + Flask** para gerenciamento de atendimentos, pacientes, prescrições e rotinas de importação/exportação de arquivos.

## Visão geral

Este projeto está organizado em módulos, com separação entre:

- **routes/**: rotas e endpoints da aplicação
- **services/**: regras de negócio e serviços auxiliares
- **templates/**: páginas HTML renderizadas pelo Flask
- **arquivos/**: diretórios de entrada e saída para processamento de arquivos

## Estrutura do projeto

```text
ATENDIMENTO_V1.0/
├── arquivos/
│   ├── entrada/
│   └── saida/
├── routes/
│   ├── __init__.py
│   ├── api.py
│   ├── atendimentos.py
│   ├── dashboard.py
│   ├── exportacao.py
│   ├── importacao.py
│   ├── pacientes.py
│   └── prescricoes.py
├── services/
│   ├── __init__.py
│   ├── arquivo_service.py
│   ├── exportacao_service.py
│   ├── importacao_service-1.py
│   ├── importacao_service.py
│   └── prescricao_service.py
├── templates/
│   ├── atendimentos/
│   ├── pacientes/
│   ├── prescricoes/
│   ├── base.html
│   ├── exportar.html
│   ├── importar.html
│   └── index.html
└── app.py / Ponto de entrada da aplicação
```
---

## Funcionalidades

- Cadastro e listagem de pacientes
- Cadastro e gerenciamento de atendimentos
- Cadastro e listagem de prescrições
- Importação de arquivos
- Exportação de arquivos
- Dashboard da aplicação
---

## Tecnologias utilizadas

- **Python 3**
- **Flask**
- **HTML / Jinja2**
- **JavaScript**
- **CSS**

