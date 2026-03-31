# Configura a conexão com o banco de dados utilizando SQLAlchemy, a partir da URL definida nas configurações da aplicação.
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.settings import Settings

settings = Settings()
# O objeto "engine" gerencia a comunicação com o banco.
engine = create_engine(settings.DATABASE_URL)

# A função "get_session" fornece uma sessão de banco de dados (Session) para uso nas operações (CRUD), geralmente sendo utilizada como dependência em frameworks web (ex: FastAPI), garantindo controle adequado de conexão e transações por requisição.
def get_session():
    yield Session(engine)
