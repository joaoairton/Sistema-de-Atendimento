from fastapi import APIRouter, Response, Depends, HTTPException
from app.schemas import PacienteCreate
from dicttoxml import dicttoxml
from app.database import get_session 
from app.models import Paciente, Atendimento
from sqlalchemy import select
from sqlalchemy.orm import Session
from xml.dom import minidom
from http import HTTPStatus
from routers.atendimento import verificar_paciente_existe, atendimento_to_dict
import re
from utils.formatters import limpar_cpf, limpar_telefone, erro_xml

router = APIRouter(prefix='/pacientes', tags=['pacientes'])

def dict_to_xml(data: dict, root_name: str = "root") -> str:
    """Converte dicionário para XML formatado"""
    xml_bytes = dicttoxml(
        data,
        custom_root=root_name,
        attr_type=False
    )
    # Formata o XML para ficar legível
    dom = minidom.parseString(xml_bytes)
    return dom.toprettyxml(indent="  ")

def pacientes_para_xml(pacientes: list[Paciente]) -> str:
    """Converte lista de pacientes para XML"""
    if not pacientes:
        return '<?xml version="1.0" encoding="UTF-8"?>\n<pacientes/>'
    
    pacientes_dict = []
    for paciente in pacientes:
        paciente_dict = {
            "cpf": paciente.cpf,
            "nome": paciente.nome,
        }
        
        if paciente.data_nasc:
            paciente_dict["data_nasc"] = str(paciente.data_nasc)
        
        if paciente.telefone:
            paciente_dict["telefone"] = paciente.telefone
        
        if paciente.email:
            paciente_dict["email"] = paciente.email
        
        if paciente.data_cadastro:
            paciente_dict["data_cadastro"] = str(paciente.data_cadastro)
        
        pacientes_dict.append(paciente_dict)
    
    return dict_to_xml(
        {"paciente": pacientes_dict},
        root_name="pacientes"
    )

def validar_paciente(cpf, nome):
    """
    Valida os dois campos obrigatórios do cadastro de paciente.
    Retorna uma lista de erros — se vazia, os dados são válidos.
    """
    erros = []
    # CPF obrigatório e com exatamente 11 dígitos numéricos
    if not cpf:
        erros.append("CPF é obrigatório.")
    elif not cpf.isdigit():
        erros.append("CPF deve conter apenas números.")
    elif len(cpf) != 11:
        erros.append(f"CPF deve ter 11 dígitos. Você informou {len(cpf)}.")

    # Nome obrigatório e não pode ser só espaços
    if not nome or not nome.strip():
        erros.append("Nome é obrigatório.")

    return erros

@router.get("/", response_class=Response)
async def listar_pacientes(session: Session = Depends(get_session)):
    pacientes = session.scalars(select(Paciente)).all()
    xml_content = pacientes_para_xml(pacientes)
    return Response(content=xml_content, media_type="application/xml")

@router.post("/", response_class=Response, status_code=HTTPStatus.CREATED)
async def criar_paciente(paciente_data: PacienteCreate,  session: Session = Depends(get_session)):
    """Cadastra um novo paciente e retorna os dados em XML"""
    paciente_data.cpf = limpar_cpf(paciente_data.cpf)
    # Verifica se o CPF já existe
    paciente_existente = session.scalar(
        select(Paciente).where(Paciente.cpf == paciente_data.cpf)
    )
    
    if paciente_existente:
        # Retorna erro em XML
        error_xml = dict_to_xml(
            {
                "erro": {
                    "codigo": "CPF_DUPLICADO",
                    "mensagem": f"Paciente com CPF {paciente_data.cpf} já cadastrado"
                }
            },
            root_name="erro"
        )
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=error_xml,
            headers={"Content-Type": "application/xml"}
        )
    
    # Cria novo paciente
    novo_paciente = Paciente(
        cpf=paciente_data.cpf,
        nome=paciente_data.nome,
        data_nasc=paciente_data.data_nasc,
        telefone= limpar_telefone(paciente_data.telefone),
        email=paciente_data.email
    )
    
    session.add(novo_paciente)
    session.commit()
    session.refresh(novo_paciente)
    
    # Retorna o paciente criado em XML
    xml_content = dict_to_xml(
        {
            "paciente": {
                "cpf": novo_paciente.cpf,
                "nome": novo_paciente.nome,
                "data_nasc": str(novo_paciente.data_nasc) if novo_paciente.data_nasc else None,
                "telefone": novo_paciente.telefone,
                "email": novo_paciente.email,
                "data_cadastro": str(novo_paciente.data_cadastro)
            }
        },
        root_name="paciente_criado"
    )

    
    return Response(
        content=xml_content,
        media_type="application/xml",
        status_code=HTTPStatus.CREATED
    )

@router.get("/{cpf}", response_class=Response)
async def buscar_paciente_por_cpf(
    cpf: str,
    session: Session = Depends(get_session)
):
    """Busca um paciente pelo CPF e retorna em XML. :D"""
    # Limpa o CPF recebido na URL
    cpf_limpo = limpar_cpf(cpf)
    
    if len(cpf_limpo) != 11:
        error_xml = dict_to_xml(
            {
                "erro": {
                    "codigo": "CPF_INVALIDO",
                    "mensagem": "CPF deve conter 11 dígitos numéricos!!!"
                }
            },
            root_name="erro"
        )
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=error_xml,
            headers={"Content-Type": "application/xml"}
        )
    
    paciente = session.scalar(
        select(Paciente).where(Paciente.cpf == cpf_limpo)
    )
    
    if not paciente:
        error_xml = dict_to_xml(
            {
                "erro": {
                    "codigo": "PACIENTE_NAO_ENCONTRADO",
                    "mensagem": f"Paciente com CPF {cpf_limpo} não encontrado"
                }
            },
            root_name="erro"
        )
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=error_xml,
            headers={"Content-Type": "application/xml"}
        )
    
    paciente_dict = {
        "cpf": paciente.cpf,
        "nome": paciente.nome
    }
    
    if paciente.data_nasc:
        paciente_dict["data_nasc"] = str(paciente.data_nasc)
    
    if paciente.telefone:
        paciente_dict["telefone"] = paciente.telefone
    
    if paciente.email:
        paciente_dict["email"] = paciente.email
    
    if paciente.data_cadastro:
        paciente_dict["data_cadastro"] = str(paciente.data_cadastro)
    
    xml_content = dict_to_xml(
        {"paciente": paciente_dict},
        root_name="paciente_encontrado"
    )
    
    return Response(content=xml_content, media_type="application/xml")

@router.put("/{cpf}", response_class=Response)
async def atualizar_paciente(
    cpf: str,
    paciente_data: PacienteCreate,
    session: Session = Depends(get_session)
):
    """Atualiza os dados de um paciente existente"""
    # Limpa o CPF da URL
    cpf_limpo_url = limpar_cpf(cpf)
    
    if len(cpf_limpo_url) != 11:
        error_xml = dict_to_xml(
            {
                "erro": {
                    "codigo": "CPF_INVALIDO",
                    "mensagem": "CPF na URL deve conter 11 dígitos numéricos"
                }
            },
            root_name="erro"
        )
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=error_xml,
            headers={"Content-Type": "application/xml"}
        )
    
    paciente = session.scalar(
        select(Paciente).where(Paciente.cpf == cpf_limpo_url)
    )
    
    if not paciente:
        error_xml = dict_to_xml(
            {
                "erro": {
                    "codigo": "PACIENTE_NAO_ENCONTRADO",
                    "mensagem": f"Paciente com CPF {cpf_limpo_url} não encontrado"
                }
            },
            root_name="erro"
        )
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=error_xml,
            headers={"Content-Type": "application/xml"}
        )
    
    # Verifica se o novo CPF (se alterado) já existe
    if paciente_data.cpf != cpf_limpo_url:
        paciente_existente = session.scalar(
            select(Paciente).where(Paciente.cpf == paciente_data.cpf)
        )
        if paciente_existente:
            error_xml = dict_to_xml(
                {
                    "erro": {
                        "codigo": "CPF_DUPLICADO",
                        "mensagem": f"CPF {paciente_data.cpf} já está cadastrado"
                    }
                },
                root_name="erro"
            )
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=error_xml,
                headers={"Content-Type": "application/xml"}
            )
    
    # Atualiza os dados
    paciente.cpf = limpar_cpf(paciente_data.cpf)
    paciente.nome = paciente_data.nome
    paciente.data_nasc = paciente_data.data_nasc
    paciente.telefone = limpar_telefone(paciente_data.telefone) 
    paciente.email = paciente_data.email
    
    session.commit()
    session.refresh(paciente)
    
    # Retorna o paciente atualizado em XML
    paciente_dict = {
        "cpf": paciente.cpf,
        "nome": paciente.nome,
        "data_nasc": str(paciente.data_nasc) if paciente.data_nasc else None,
        "telefone": paciente.telefone,
        "email": paciente.email,
        "data_cadastro": str(paciente.data_cadastro)
    }
    
    xml_content = dict_to_xml(
        {"paciente": paciente_dict},
        root_name="paciente_atualizado"
    )
    
    return Response(content=xml_content, media_type="application/xml")

@router.delete("/{cpf}", response_class=Response, status_code=HTTPStatus.OK)
async def deletar_paciente(
    cpf: str,
    session: Session = Depends(get_session)
):
    """Remove um paciente pelo CPF"""
    # Limpa o CPF da URL
    cpf_limpo = limpar_cpf(cpf)
    
    if len(cpf_limpo) != 11:
        error_xml = dict_to_xml(
            {
                "erro": {
                    "codigo": "CPF_INVALIDO",
                    "mensagem": "CPF deve conter 11 dígitos numéricos"
                }
            },
            root_name="erro"
        )
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=error_xml,
            headers={"Content-Type": "application/xml"}
        )
    
    paciente = session.scalar(
        select(Paciente).where(Paciente.cpf == cpf_limpo)
    )
    
    if not paciente:
        error_xml = dict_to_xml(
            {
                "erro": {
                    "codigo": "PACIENTE_NAO_ENCONTRADO",
                    "mensagem": f"Paciente com CPF {cpf_limpo} não encontrado"
                }
            },
            root_name="erro"
        )
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=error_xml,
            headers={"Content-Type": "application/xml"}
        )
    
    session.delete(paciente)
    session.commit()
    
    # Retorna mensagem de sucesso
    xml_content = dict_to_xml(
        {
            "sucesso": {
                "mensagem": f"Paciente com CPF {cpf_limpo} removido com sucesso"
            }
        },
        root_name="resposta"
    )
    
    return Response(content=xml_content, media_type="application/xml")

@router.get("/atendimento/{cpf}", response_class=Response)
async def listar_atendimentos_por_paciente(cpf: str, session: Session = Depends(get_session)):
    """Consulta os dados de atendimento do paciente de acordo com seu CPF"""
    try:
        cpf_limpo = limpar_cpf(cpf)
    except ValueError as e:
        error_xml = dict_to_xml(
            {"erro": {"codigo": "CPF_INVALIDO", "mensagem": str(e)}},
            root_name="erro"
        )
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=error_xml, headers={"Content-Type": "application/xml"})

    # Verifica se paciente existe
    verificar_paciente_existe(session, cpf_limpo)

    atendimentos = session.scalars(
        select(Atendimento).where(Atendimento.cpf_paciente == cpf_limpo)
    ).all()

    if not atendimentos:
        return Response(content='<?xml version="1.0" encoding="UTF-8"?>\n<atendimentos/>', media_type="application/xml")

    lista = [atendimento_to_dict(a) for a in atendimentos]
    xml = dict_to_xml({"atendimento": lista}, root_name="atendimentos")
    return Response(content=xml, media_type="application/xml")