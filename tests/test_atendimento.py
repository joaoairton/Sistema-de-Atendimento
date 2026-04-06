
"""
Testes para o endpoint de criação de atendimentos
"""

from http import HTTPStatus
from datetime import date, time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import xml.etree.ElementTree as ET

from app.models import Paciente, Atendimento


# ======================== Helper Functions ========================

def parse_xml(xml_content: str) -> ET.Element:
    """Analisa a string XML e retorna o elemento raiz."""
    return ET.fromstring(xml_content)


def assert_xml_error(xml_content: bytes, expected_code: str, expected_message_part: str):
    """Verifica se a resposta de erro XML contém o código e parte da mensagem."""
    root = parse_xml(xml_content)
    code = root.find(".//codigo")
    message = root.find(".//mensagem")
    assert code is not None, "Elemento 'codigo' não encontrado"
    assert message is not None, "Elemento 'mensagem' não encontrado"
    assert code.text == expected_code
    assert expected_message_part in message.text


def create_patient(session: Session, cpf: str, nome: str) -> Paciente:
    """Cria um paciente para os testes."""
    patient = Paciente(cpf=cpf, nome=nome)
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient


# ======================== Tests ========================

class TestCreateAtendimento:
    """Testes para POST /atendimentos/"""

    def test_create_valid_atendimento(self, client: TestClient, db_session: Session):
        """Cria um atendimento válido e verifica a resposta XML."""
        # Cria paciente primeiro
        create_patient(db_session, "12345678901", "João Silva")
        
        dados = {
            "cpf_paciente": "12345678901",
            "tipo": "C",
            "crm_medico": "SP123456",
            "especialidade": "CARDIOLOGIA",
            "convenio": "UNIMED",
            "carteirinha": "123456789",
            "status": "ABERTO",
            "observacao": "Paciente com dor no peito",
            "cid_principal": "I10",
            "procedimento": "CONSULTA"
        }
        
        response = client.post("/atendimentos/", json=dados)
        assert response.status_code == HTTPStatus.CREATED
        assert response.headers["content-type"] == "application/xml"
        
        root = parse_xml(response.content)
        assert root.tag == "atendimento_criado"
        atendimento = root.find(".//atendimento")
        assert atendimento is not None
        assert atendimento.find(".//cpf_paciente").text == "12345678901"
        assert atendimento.find(".//status").text == "ABERTO"

    def test_create_atendimento_paciente_nao_existe(self, client: TestClient):
        """Tenta criar atendimento com CPF de paciente inexistente."""
        dados = {
            "cpf_paciente": "99999999999",
            "tipo": "C",
            "crm_medico": "SP123456",
            "especialidade": "CARDIOLOGIA"
        }
        
        response = client.post("/atendimentos/", json=dados)
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert_xml_error(
            response.content,
            "PACIENTE_NAO_ENCONTRADO",
            "Paciente com CPF 99999999999 não encontrado"
        )

    def test_create_atendimento_cpf_invalido(self, client: TestClient):
        """Tenta criar atendimento com CPF inválido (menos de 11 dígitos)."""
        dados = {
            "cpf_paciente": "12345",
            "tipo": "C",
            "crm_medico": "SP123456"
        }
        
        response = client.post("/atendimentos/", json=dados)
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert_xml_error(
            response.content,
            "CPF_INVALIDO",
            "CPF deve conter 11 dígitos"
        )

    def test_create_atendimento_status_invalido(self, client: TestClient, db_session: Session):
        """Tenta criar atendimento com status inválido."""
        create_patient(db_session, "12345678901", "João Silva")
        
        dados = {
            "cpf_paciente": "12345678901",
            "status": "STATUS_INEXISTENTE",
            "crm_medico": "SP123456"
        }
        
        response = client.post("/atendimentos/", json=dados)
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert_xml_error(
            response.content,
            "STATUS_INVALIDO",
            "Status inválido"
        )

    def test_create_atendimento_crm_invalido(self, client: TestClient, db_session: Session):
        """Tenta criar atendimento com CRM em formato inválido."""
        create_patient(db_session, "12345678901", "João Silva")
        
        dados = {
            "cpf_paciente": "12345678901",
            "crm_medico": "123456",  # Sem UF
            "tipo": "C"
        }
        
        response = client.post("/atendimentos/", json=dados)
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert_xml_error(
            response.content,
            "CRM_INVALIDO",
            "CRM deve conter o formato: UF seguido de números"
        )

    def test_create_atendimento_valor_negativo(self, client: TestClient, db_session: Session):
        """Tenta criar atendimento com valor de procedimentos negativo."""
        create_patient(db_session, "12345678901", "João Silva")
        
        dados = {
            "cpf_paciente": "12345678901",
            "valor_procedimentos": -100.50,
            "crm_medico": "SP123456"
        }
        
        response = client.post("/atendimentos/", json=dados)
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert_xml_error(
            response.content,
            "VALOR_INVALIDO",
            "Valor de procedimentos não pode ser negativo"
        )

    def test_create_atendimento_quantidade_negativa(self, client: TestClient, db_session: Session):
        """Tenta criar atendimento com quantidade de medicamentos negativa."""
        create_patient(db_session, "12345678901", "João Silva")
        
        dados = {
            "cpf_paciente": "12345678901",
            "qtd_medicamentos": -5,
            "crm_medico": "SP123456"
        }
        
        response = client.post("/atendimentos/", json=dados)
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert_xml_error(
            response.content,
            "QUANTIDADE_INVALIDA",
            "Quantidade de medicamentos não pode ser negativa"
        )

    def test_create_atendimento_data_sem_hora(self, client: TestClient, db_session: Session):
        """Tenta criar atendimento com data de encerramento sem hora."""
        create_patient(db_session, "12345678901", "João Silva")
        
        dados = {
            "cpf_paciente": "12345678901",
            "data_encerramento": "2025-12-31",  # Só data, sem hora
            "crm_medico": "SP123456"
        }
        
        response = client.post("/atendimentos/", json=dados)
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert_xml_error(
            response.content,
            "DATA_HORA_INCOMPLETA",
            "Data e hora de encerramento devem ser fornecidas juntas"
        )

    def test_create_atendimento_com_encerramento_completo(self, client: TestClient, db_session: Session):
        """Cria atendimento com data e hora de encerramento."""
        create_patient(db_session, "12345678901", "João Silva")
        
        dados = {
            "cpf_paciente": "12345678901",
            "crm_medico": "SP123456",
            "status": "ENCERRADO",
            "data_encerramento": "2025-12-31",
            "hora_encerramento": "14:30:00"
        }
        
        response = client.post("/atendimentos/", json=dados)
        assert response.status_code == HTTPStatus.CREATED
        
        root = parse_xml(response.content)
        atendimento = root.find(".//atendimento")
        assert atendimento.find(".//status").text == "ENCERRADO"
        assert atendimento.find(".//data_encerramento") is not None
        assert atendimento.find(".//hora_encerramento") is not None

    def test_create_atendimento_campos_opcionais_vazios(self, client: TestClient, db_session: Session):
        """Cria atendimento com campos opcionais vazios ou nulos."""
        create_patient(db_session, "12345678901", "João Silva")
        
        dados = {
            "cpf_paciente": "12345678901",
            "crm_medico": "SP123456"
            # Todos os outros campos são opcionais e não enviados
        }
        
        response = client.post("/atendimentos/", json=dados)
        assert response.status_code == HTTPStatus.CREATED
        
        root = parse_xml(response.content)
        atendimento = root.find(".//atendimento")
        assert atendimento.find(".//status").text == "ABERTO"  # Status padrão