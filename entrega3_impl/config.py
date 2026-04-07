# config.py — configuração central do projeto Entrega 3
# Banco independente da Entrega 2: db_atendimento_xml

import os
import psycopg2
import psycopg2.extras

# Credenciais — use variáveis de ambiente em produção
DB_HOST     = os.getenv("DB_HOST",     "localhost")
DB_NAME     = os.getenv("DB_NAME",     "db_atendimento_xml")
DB_USER     = os.getenv("DB_USER",     "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "SUA_SENHA_AQUI")

SECRET_KEY  = os.getenv("FLASK_SECRET_KEY", "entrega3_xml_2026")

# Caminhos dos schemas XSD
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
SCHEMA_DIR  = os.path.join(BASE_DIR, "schemas")
XSD_FINALIZACAO  = os.path.join(SCHEMA_DIR, "finalizacao.xsd")
XSD_FIN_RETORNO  = os.path.join(SCHEMA_DIR, "financeiro_retorno.xsd")

# Pastas de XMLs
XML_SAIDA   = os.path.join(BASE_DIR, "xml_gerados")
XML_ENTRADA = os.path.join(BASE_DIR, "xml_entrada")

def get_db():
    """Abre e retorna uma conexão com o banco db_atendimento_xml."""
    return psycopg2.connect(
        host=DB_HOST, database=DB_NAME,
        user=DB_USER, password=DB_PASSWORD,
    )

def get_cur(db):
    """Cursor com acesso por nome de coluna: row['cpf']."""
    return db.cursor(cursor_factory=psycopg2.extras.DictCursor)

# XSDs do Estoque
XSD_ESTOQUE_CONSULTA = os.path.join(SCHEMA_DIR, "consulta.xsd")
XSD_ESTOQUE_RESERVA  = os.path.join(SCHEMA_DIR, "reserva.xsd")
XSD_ESTOQUE_RESPOSTA = os.path.join(SCHEMA_DIR, "resposta.xsd")
