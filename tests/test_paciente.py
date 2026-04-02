"""
Conjunto de testes para os endpoints de pacientes.
Este módulo utiliza pytest e o TestClient do FastAPI para testar todas as operações CRUD
no endpoint /pacientes, bem como o endpoint que lista os atendimentos
por CPF do paciente.
Os testes são isolados utilizando um banco de dados SQLite em memória e sobrescrevendo
a dependência get_session.
"""


from http import HTTPStatus
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import xml.etree.ElementTree as ET
from app.models import Paciente


# ======================== Helper functions ========================

def parse_xml(xml_content: str) -> ET.Element:
    """Analisa a string XML e retorna o elemento raiz."""
    return ET.fromstring(xml_content)


def assert_xml_error(xml_content: str, expected_code: str, expected_message: str):
    """Verifique se a resposta de erro XML contém o código e a mensagem fornecidos."""
    root = parse_xml(xml_content)
    # The error structure: <erro><codigo>...</codigo><mensagem>...</mensagem></erro>
    assert root.tag == "erro"
    code = root.find("codigo")
    message = root.find("mensagem")
    assert code is not None and code.text == expected_code
    assert message is not None and message.text == expected_message


def create_patient(session: Session, cpf: str, nome: str, **kwargs) -> Paciente:
    """Auxiliar para criar um paciente no banco de dados."""
    patient = Paciente(
        cpf=cpf,
        nome=nome,
        data_nasc=kwargs.get("data_nasc"),
        telefone=kwargs.get("telefone"),
        email=kwargs.get("email"),
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient


def create_atendimento(session: Session, cpf_paciente: str, **kwargs):
    """Auxiliar na elaboração de um atendimento para um paciente."""
    # Ajuste os atributos do modelo Atendimento de acordo com seu esquema.
    # Este exemplo pressupõe que Atendimento tenha um campo `cpf_paciente`.
    from app.models import Atendimento 
    atend = Atendimento(
        cpf_paciente=cpf_paciente,
        **kwargs
    )
    session.add(atend)
    session.commit()
    session.refresh(atend)
    return atend

def pacientes_para_xml(pacientes: list[Paciente]) -> str:
    """Converte lista de pacientes para XML com múltiplas tags <paciente>"""
    if not pacientes:
        return '<?xml version="1.0" encoding="UTF-8"?>\n<pacientes/>'
    
    root = ET.Element("pacientes")
    for p in pacientes:
        paciente_elem = ET.SubElement(root, "paciente")
        ET.SubElement(paciente_elem, "cpf").text = p.cpf
        ET.SubElement(paciente_elem, "nome").text = p.nome
        if p.data_nasc:
            ET.SubElement(paciente_elem, "data_nasc").text = str(p.data_nasc)
        if p.telefone:
            ET.SubElement(paciente_elem, "telefone").text = p.telefone
        if p.email:
            ET.SubElement(paciente_elem, "email").text = p.email
        if p.data_cadastro:
            ET.SubElement(paciente_elem, "data_cadastro").text = str(p.data_cadastro)
    
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")

# ======================== Testes ========================
class TestListPatients:
    """Testes para GET /pacientes/"""

    def test_list_empty(self, client: TestClient):
        """Quando não houver pacientes, retorne um elemento <pacientes/> vazio.."""
        response = client.get("/pacientes/")
        assert response.status_code == HTTPStatus.OK
        assert response.headers["content-type"] == "application/xml"

        root = parse_xml(response.content)
        assert root.tag == "pacientes"
        # Não deve ter children.
        assert len(root) == 0

    def test_list_multiple_patients(self, client: TestClient, db_session: Session):
        """Quando houver pacientes, retorne-os todos em formato XML."""
        # Criar dois pacientes.
        create_patient(db_session, "12345678901", "João Silva", telefone="11999999999")
        create_patient(db_session, "98765432100", "Maria Souza", email="maria@example.com")

        response = client.get("/pacientes/")
        assert response.status_code == HTTPStatus.OK

        root = parse_xml(response.content)
        assert root.tag == "pacientes"
        # Deverá haver duas crianças <paciente>.
        patients = root.findall("paciente")
        patients = root.findall(".//item")  # busca em qualquer profundidade
        assert len(patients) == 2

        # E para extrair os CPFs:
        cpfs = [p.find("cpf").text for p in patients]
        assert len(patients) == 2

        # Verifique se os dados estão corretos (a ordem pode não ser garantida, por isso verificamos a existência).
        cpfs = [p.find("cpf").text for p in patients]
        assert "12345678901" in cpfs
        assert "98765432100" in cpfs

class TestCreatePatient:
    """Tests for POST /pacientes/"""

    def test_create_valid_patient(self, client: TestClient):
        """Criar um paciente com dados válidos e receber uma representação XML."""
        data = {
            "cpf": "11122233344",
            "nome": "Carlos Alberto",
            "data_nasc": "1990-01-01",
            "telefone": "11988887777",
            "email": "carlos@example.com",
        }
        response = client.post("/pacientes/", json=data)
        assert response.status_code == HTTPStatus.CREATED
        assert response.headers["content-type"] == "application/xml"

        root = parse_xml(response.content)
        assert root.tag == "paciente_criado"
        paciente = root.find("paciente")
        assert paciente is not None
        assert paciente.find("cpf").text == "11122233344"
        assert paciente.find("nome").text == "Carlos Alberto"
        assert paciente.find("data_nasc").text == "1990-01-01"
        assert paciente.find("telefone").text == "11988887777"
        assert paciente.find("email").text == "carlos@example.com"
        assert paciente.find("data_cadastro") is not None

    def test_create_duplicate_cpf(self, client: TestClient, db_session: Session):
        """A tentativa de criar um paciente com um CPF existente retorna um erro XML."""
        # Criando um paciente primeiro.
        create_patient(db_session, "11122233344", "Existing User")

        data = {
            "cpf": "11122233344",
            "nome": "Another Name",
            "data_nasc": "1990-01-01",   # adicionado
            "telefone": "11999999999",
            "email": "teste@example.com", # adicionado
        }
        response = client.post("/pacientes/", json=data)
        print(response)
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.headers["content-type"] == "application/xml"
        assert_xml_error(response.content, "CPF_DUPLICADO", "Paciente com CPF 11122233344 já cadastrado")

    def test_create_missing_required_fields(self, client: TestClient):
        """CPF ou nome ausente deve ser rejeitado (o endpoint pode contar com validação do Pydantic)."""
        # O endpoint usa o esquema PacienteCreate, o que presumivelmente torna cpf e nome obrigatórios.
        # Podemos testar um campo ausente.
        data = {"cpf": "11122233344"}  # missing nome
        response = client.post("/pacientes/", json=data)
        # O erro de validação é gerado pelo FastAPI/Pydantic, que retorna 422.
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

        assert "application/xml" in response.headers["content-type"]


class TestGetPatientByCPF:
    """Tests for GET /pacientes/{cpf}"""

    def test_get_existing_patient(self, client: TestClient, db_session: Session):
        """Recuperar um paciente pelo CPF e obter sua representação em XML."""
        patient = create_patient(db_session, "12345678901", "João da Silva", telefone="11999999999")

        response = client.get("/pacientes/12345678901")
        assert response.status_code == HTTPStatus.OK
        assert response.headers["content-type"] == "application/xml"

        root = parse_xml(response.content)
        assert root.tag == "paciente_encontrado"
        paciente = root.find("paciente")
        assert paciente.find("cpf").text == "12345678901"
        assert paciente.find("nome").text == "João da Silva"
        assert paciente.find("telefone").text == "11999999999"
        # O parâmetro Data_nasc não foi definido, portanto, deve estar ausente.
        assert paciente.find("data_nasc") is None

    def test_get_non_existing_patient(self, client: TestClient):
        """A mensagem "CPF não encontrado" retorna o erro 404 (Not Found) com erro XML."""
        response = client.get("/pacientes/00000000000")
        print(response)
        assert response.status_code == HTTPStatus.NOT_FOUND
        print(response.content)
        assert_xml_error(response.content, "PACIENTE_NAO_ENCONTRADO", "Paciente com CPF 00000000000 não encontrado")

    def test_get_invalid_cpf_format(self, client: TestClient):
        """O CPF com comprimento incorreto ou que não contenha dígitos retorna 400 (Bad Request)."""
        response = client.get("/pacientes/12345")
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert_xml_error(response.content, "CPF_INVALIDO", "CPF deve conter 11 dígitos numéricos!!!")


class TestUpdatePatient:
    """Testes para PUT /pacientes/{cpf}"""

    def test_update_existing_patient(self, client: TestClient, db_session: Session):
        """Atualize os dados de um paciente e receba o XML atualizado."""
        # Criando um paciente.
        create_patient(db_session, "11122233344", "Old Name", telefone="111111111")

        update_data = {
            "cpf": "11122233344",  # mesmo CPF
            "nome": "New Name",
            "telefone": "2222222222",
            "email": "new@example.com",
            "data_nasc": "1990-01-01"
        }
        
        response = client.put("/pacientes/11122233344", json=update_data)
        assert response.status_code == HTTPStatus.OK
        assert response.headers["content-type"] == "application/xml"

        root = parse_xml(response.content)
        assert root.tag == "paciente_atualizado"
        paciente = root.find("paciente")
        assert paciente.find("cpf").text == "11122233344"
        assert paciente.find("nome").text == "New Name"
        assert paciente.find("telefone").text == "2222222222"
        assert paciente.find("email").text == "new@example.com"
        assert paciente.find("data_nasc").text == "1990-01-01"

    def test_update_with_different_cpf_that_exists(self, client: TestClient, db_session: Session):
        """Alterar o CPF para um já utilizado por outro paciente deverá falhar."""
        # Criando dois pacientes.
        create_patient(db_session, "11122233344", "Patient A")
        create_patient(db_session, "99988877766", "Patient B")

        # Tente atualizar o Paciente B para o CPF do Paciente A.
        update_data = {
            "cpf": "11122233344",  # novo CPF
            "nome": "Patient B Updated",
            "telefone": "2222222222",
            "email": "pacientb@example.com",
            "data_nasc": "1990-01-01"
        }
        response = client.put("/pacientes/99988877766", json=update_data)
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert_xml_error(response.content, "CPF_DUPLICADO", "CPF 11122233344 já está cadastrado")

    def test_update_non_existing_patient(self, client: TestClient):
        """Atualizar um paciente que não existe retorna o erro 404 (Not  Found)."""
        update_data = {"cpf": "00000000000", "nome": "Nonexistent"}
        update_data = {
            "cpf": "00000000000",  # novo CPF
            "nome": "Nonexistent",
            "telefone": "2222222222",
            "email": "pacient_none@example.com",
            "data_nasc": "1990-01-01"
        }
        response = client.put("/pacientes/00000000000", json=update_data)
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert_xml_error(response.content, "PACIENTE_NAO_ENCONTRADO", "Paciente com CPF 00000000000 não encontrado")


class TestDeletePatient:
    """Testes para DELETE /pacientes/{cpf}"""

    def test_delete_existing_patient(self, client: TestClient, db_session: Session):
        """Ao excluir um paciente, é possível receber uma mensagem XML de sucesso."""
        create_patient(db_session, "11122233344", "To be deleted")

        response = client.delete("/pacientes/11122233344")
        assert response.status_code == HTTPStatus.OK
        assert response.headers["content-type"] == "application/xml"

        root = parse_xml(response.content)
        assert root.tag == "resposta"
        sucesso = root.find("sucesso")
        assert sucesso is not None
        assert sucesso.find("mensagem").text == "Paciente com CPF 11122233344 removido com sucesso"

        # Verifique se foi realmente excluído.
        response_after = client.get("/pacientes/11122233344")
        assert response_after.status_code == HTTPStatus.NOT_FOUND

    def test_delete_non_existing_patient(self, client: TestClient):
        """Excluir um paciente que não existe retorna o erro 404 (Not Found)."""
        response = client.delete("/pacientes/00000000000")
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert_xml_error(response.content, "PACIENTE_NAO_ENCONTRADO", "Paciente com CPF 00000000000 não encontrado")


class TestListAtendimentosByPatient:
    """Tests para GET /pacientes/atendimento/{cpf} ---> Porém sujeito a falha pois tem que verificar os endpoints de Atendimento"""

    def test_list_atendimentos_empty(self, client: TestClient, db_session: Session):
        """Paciente existe mas não tem atendimento, retornar vazio <atendimentos/>."""
        create_patient(db_session, "12345678901", "Patient With No Atendimentos")

        response = client.get("/pacientes/atendimento/12345678901")
        assert response.status_code == HTTPStatus.OK
        assert response.headers["content-type"] == "application/xml"
        root = parse_xml(response.content)
        assert root.tag == "atendimentos"
        assert len(root) == 0

    def test_list_atendimentos_with_data(self, client: TestClient, db_session: Session):
        """O paciente tem atendimentos, retorne-os em XML."""
        patient_cpf = "12345678901"
        create_patient(db_session, patient_cpf, "Patient With Atendimentos")

        # Crie alguns atendimentos. Ajuste os campos para que correspondam ao seu modelo.
        create_atendimento(db_session, patient_cpf, data="2025-01-01", descricao="Consulta")
        create_atendimento(db_session, patient_cpf, data="2025-02-01", descricao="Retorno")

        response = client.get(f"/pacientes/atendimento/{patient_cpf}")
        assert response.status_code == HTTPStatus.OK
        assert response.headers["content-type"] == "application/xml"

        root = parse_xml(response.content)
        assert root.tag == "atendimentos"
        atendimentos = root.findall("atendimento")
        assert len(atendimentos) == 2

        # Opcionalmente, verifique o conteúdo.
        descs = [a.find("descricao").text for a in atendimentos]
        assert "Consulta" in descs
        assert "Retorno" in descs

    def test_list_atendimentos_patient_not_found(self, client: TestClient):
        """O CPF do paciente não existe -> erro XML 404 (Not Found)."""
        response = client.get("/pacientes/atendimento/99999999999")
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert_xml_error(response.content, "PACIENTE_NAO_ENCONTRADO", "Paciente com CPF 99999999999 não encontrado")

    def test_list_atendimentos_invalid_cpf(self, client: TestClient):
        """CPF com comprimento incorreto -> erro XML 400 (Bad Request)."""
        response = client.get("/pacientes/atendimento/12345")
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert_xml_error(response.content, "CPF_INVALIDO", "CPF deve conter 11 dígitos numéricos!!!")