import os
import psycopg2
import psycopg2.extras

# -----------------------------------------------------------------------------
# Configurações da aplicação
# -----------------------------------------------------------------------------

SECRET_KEY  = os.getenv("FLASK_SECRET_KEY", "hospital_atendimento_2026")
DB_HOST     = os.getenv("DB_HOST",     "localhost")
DB_NAME     = os.getenv("DB_NAME",     "db_atendimento")
DB_USER     = os.getenv("DB_USER",     "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "senha")


def get_db():
    """
    Abre e retorna uma nova conexão com o banco.
    Sempre feche no bloco finally da rota que chamou esta função.
    """
    return psycopg2.connect(
        host=DB_HOST, database=DB_NAME,
        user=DB_USER, password=DB_PASSWORD,
        client_encoding="utf8"
    )


def get_cursor(db):
    """Cursor que permite acessar colunas pelo nome: row["cpf"]."""
    return db.cursor(cursor_factory=psycopg2.extras.DictCursor)
