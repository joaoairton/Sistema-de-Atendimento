# app/atendimentos.py
from fastapi import APIRouter, Depends, HTTPException
from http import HTTPStatus 
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import date, datetime
from app.database import get_session
from app.models import Atendimento, Paciente
from app.schemas import AtendimentoCreate
from app.xml_utils import dict_to_xml, atendimento_to_dict
from utils.formatters import limpar_cpf 


router = APIRouter(prefix='/atendimentos', tags=['atendimentos'])
def validar_crm(crm: str) -> bool:
    """Valida formato do CRM: 2 letras (UF) seguido de números"""
    import re
    pattern = r'^[A-Z]{2}\d+$'
    return bool(re.match(pattern, crm))

def verificar_paciente_existe(session: Session, cpf: str):
    paciente = session.scalar(select(Paciente).where(Paciente.cpf == cpf))      
    if not paciente:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=dict_to_xml(
                {"erro": {"codigo": "PACIENTE_NAO_ENCONTRADO", "mensagem": f"Paciente com CPF {cpf} não encontrado"}},
                root_name="erro"
            ),
            headers={"Content-Type": "application/xml"}
        )

@router.get("/", response_class=Response)
async def listar_atendimentos(session: Session = Depends(get_session)):
    """Lista todos os atendimentos"""
    atendimentos = session.scalars(select(Atendimento).order_by(Atendimento.id_atendimento)).all()
    if not atendimentos:
        return Response(content='<?xml version="1.0" encoding="UTF-8"?>\n<atendimentos/>', media_type="application/xml")
    
    lista = [atendimento_to_dict(a) for a in atendimentos]
    xml = dict_to_xml({"atendimento": lista}, root_name="atendimentos")
    return Response(content=xml, media_type="application/xml")

@router.get("/{id_atendimento}", response_class=Response)
async def buscar_atendimento(id_atendimento: int, session: Session = Depends(get_session)):
    atendimento = session.get(Atendimento, id_atendimento)
    if not atendimento:
        error_xml = dict_to_xml(
            {"erro": {"codigo": "ATENDIMENTO_NAO_ENCONTRADO", "mensagem": f"Atendimento {id_atendimento} não encontrado"}},
            root_name="erro"
        )
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=error_xml, headers={"Content-Type": "application/xml"})
    xml = dict_to_xml({"atendimento": atendimento_to_dict(atendimento)}, root_name="atendimento_encontrado")
    return Response(content=xml, media_type="application/xml")

@router.post("/", response_class=Response, status_code=HTTPStatus.CREATED)
async def criar_atendimento(
    dados: AtendimentoCreate,
    session: Session = Depends(get_session)
):
    """Cria um novo atendimento e retorna os dados em XML"""
    
    # 1. Valida e limpa o CPF
    try:
        cpf_limpo = limpar_cpf(dados.cpf_paciente)
    except ValueError as e:
        error_xml = dict_to_xml(
            {
                "codigo": "CPF_INVALIDO",
                "mensagem": str(e)
            },
            root_name="erro"
        )
        return Response(
            content=error_xml,
            media_type="application/xml",
            status_code=HTTPStatus.BAD_REQUEST
        )
    # 2. Verifica se o paciente existe
    paciente = session.scalar(
        select(Paciente).where(Paciente.cpf == cpf_limpo)
    )
    
    if not paciente:
        error_xml = dict_to_xml(
            {
                "codigo": "PACIENTE_NAO_ENCONTRADO",
                "mensagem": f"Paciente com CPF {cpf_limpo} não encontrado"
            },
            root_name="erro"
        )
        return Response(
            content=error_xml,
            media_type="application/xml",
            status_code=HTTPStatus.NOT_FOUND
        )
    
    # 3. Valida o status (se fornecido)
    if dados.status and dados.status not in ['ABERTO', 'EM_ATENDIMENTO', 'ENCERRADO', 'CANCELADO']:
        error_xml = dict_to_xml(
            {
                "codigo": "STATUS_INVALIDO",
                "mensagem": f"Status inválido: {dados.status}. Valores permitidos: ABERTO, EM_ATENDIMENTO, ENCERRADO, CANCELADO"
            },
            root_name="erro"
        )
        return Response(
            content=error_xml,
            media_type="application/xml",
            status_code=HTTPStatus.BAD_REQUEST
        )
    
    # 4. Valida CRM do médico (se fornecido)
    if dados.crm_medico and not validar_crm(dados.crm_medico):
        error_xml = dict_to_xml(
            {
                "codigo": "CRM_INVALIDO",
                "mensagem": "CRM deve conter o formato: UF seguido de números (ex: SP123456)"
            },
            root_name="erro"
        )
        return Response(
            content=error_xml,
            media_type="application/xml",
            status_code=HTTPStatus.BAD_REQUEST
        )
    
    # 5. Valida valor de procedimentos (não pode ser negativo)
    if dados.valor_procedimentos is not None and dados.valor_procedimentos < 0:
        error_xml = dict_to_xml(
            {
                "codigo": "VALOR_INVALIDO",
                "mensagem": "Valor de procedimentos não pode ser negativo"
            },
            root_name="erro"
        )
        return Response(
            content=error_xml,
            media_type="application/xml",
            status_code=HTTPStatus.BAD_REQUEST
        )
    
    # 6. Valida quantidade de medicamentos (não pode ser negativa)
    if dados.qtd_medicamentos is not None and dados.qtd_medicamentos < 0:
        error_xml = dict_to_xml(
            {
                "codigo": "QUANTIDADE_INVALIDA",
                "mensagem": "Quantidade de medicamentos não pode ser negativa"
            },
            root_name="erro"
        )
        return Response(
            content=error_xml,
            media_type="application/xml",
            status_code=HTTPStatus.BAD_REQUEST
        )
    
    # 7. Valida data e hora de encerramento (se um for fornecido, o outro também deve ser)
    if (dados.data_encerramento and not dados.hora_encerramento) or \
       (not dados.data_encerramento and dados.hora_encerramento):
        error_xml = dict_to_xml(
            {
                "codigo": "DATA_HORA_INCOMPLETA",
                "mensagem": "Data e hora de encerramento devem ser fornecidas juntas"
            },
            root_name="erro"
        )
        return Response(
            content=error_xml,
            media_type="application/xml",
            status_code=HTTPStatus.BAD_REQUEST
        )
    
    # Cria objeto
    try:
        novo = Atendimento(
            cpf_paciente=cpf_limpo,
            tipo=dados.tipo,
            crm_medico=dados.crm_medico,
            especialidade=dados.especialidade,
            convenio=dados.convenio,
            carteirinha=dados.carteirinha,
            status=dados.status or "ABERTO",
            observacao=dados.observacao,
            data_encerramento=dados.data_encerramento,
            hora_encerramento=dados.hora_encerramento,
            cid_principal=dados.cid_principal,
            procedimento=dados.procedimento,
            qtd_medicamentos=dados.qtd_medicamentos,
            valor_procedimentos=dados.valor_procedimentos,
            data_abertura=date.today(),
            hora_abertura=datetime.now().time()
        )
        
        session.add(novo)
        session.commit()
        session.refresh(novo)
        
    except Exception as e:
        session.rollback()
        error_xml = dict_to_xml(
            {
                "codigo": "ERRO_INTERNO",
                "mensagem": f"Erro ao criar atendimento: {str(e)}"
            },
            root_name="erro"
        )
        return Response(
            content=error_xml,
            media_type="application/xml",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR
        )
    
    # Retorna o atendimento criado em XML
    xml = dict_to_xml(
        {"atendimento": atendimento_to_dict(novo)},
        root_name="atendimento_criado"
    )
    return Response(
        content=xml,
        media_type="application/xml",
        status_code=HTTPStatus.CREATED
    )

@router.put("/{id_atendimento}", response_class=Response)
async def atualizar_atendimento(
    id_atendimento: int,
    dados: AtendimentoCreate,
    session: Session = Depends(get_session)
):
    atendimento = session.get(Atendimento, id_atendimento)
    if not atendimento:
        error_xml = dict_to_xml(
            {"erro": {"codigo": "ATENDIMENTO_NAO_ENCONTRADO", "mensagem": f"Atendimento {id_atendimento} não encontrado"}},
            root_name="erro"
        )
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=error_xml, headers={"Content-Type": "application/xml"})

    # Valida CPF se alterado
    if dados.cpf_paciente != atendimento.cpf_paciente:
        cpf_limpo = limpar_cpf(dados.cpf_paciente)
        verificar_paciente_existe(session, cpf_limpo)
        atendimento.cpf_paciente = cpf_limpo

    # Atualiza campos
    atendimento.tipo = dados.tipo
    atendimento.crm_medico = dados.crm_medico
    atendimento.especialidade = dados.especialidade
    atendimento.convenio = dados.convenio
    atendimento.carteirinha = dados.carteirinha
    atendimento.status = dados.status or atendimento.status
    atendimento.observacao = dados.observacao
    atendimento.data_encerramento = dados.data_encerramento
    atendimento.hora_encerramento = dados.hora_encerramento
    atendimento.cid_principal = dados.cid_principal
    atendimento.procedimento = dados.procedimento
    atendimento.qtd_medicamentos = dados.qtd_medicamentos
    atendimento.valor_procedimentos = dados.valor_procedimentos

    session.commit()
    session.refresh(atendimento)

    xml = dict_to_xml({"atendimento": atendimento_to_dict(atendimento)}, root_name="atendimento_atualizado")
    return Response(content=xml, media_type="application/xml")

@router.delete("/{id_atendimento}", response_class=Response, status_code=HTTPStatus.OK)
async def deletar_atendimento(id_atendimento: int, session: Session = Depends(get_session)):
    atendimento = session.get(Atendimento, id_atendimento)
    if not atendimento:
        error_xml = dict_to_xml(
            {"erro": {"codigo": "ATENDIMENTO_NAO_ENCONTRADO", "mensagem": f"Atendimento {id_atendimento} não encontrado"}},
            root_name="erro"
        )
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=error_xml, headers={"Content-Type": "application/xml"})

    session.delete(atendimento)
    session.commit()

    xml = dict_to_xml(
        {"sucesso": {"mensagem": f"Atendimento {id_atendimento} removido com sucesso"}},
        root_name="resposta"
    )
    return Response(content=xml, media_type="application/xml")