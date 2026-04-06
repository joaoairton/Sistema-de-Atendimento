# app/routers/prescricoes.py
from fastapi import APIRouter, Depends, HTTPException
from http import HTTPStatus
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import date, datetime
from app.database import get_session
from app.models import Prescricao, Atendimento, Paciente
from app.schemas import PrescricaoCreate
from app.xml_utils import dict_to_xml, prescricao_to_dict
from utils.formatters import limpar_cpf

router = APIRouter(prefix='/prescricoes', tags=['prescricoes'])

def validar_cpf(cpf: str) -> str:
    cpf_limpo = limpar_cpf(cpf)
    if len(cpf_limpo) != 11:
        raise ValueError('CPF deve ter 11 dígitos')
    return cpf_limpo

def verificar_paciente_existe(session: Session, cpf: str):
    cpf = validar_cpf(cpf)
    paciente = session.scalar(select(Paciente).where(Paciente.cpf == cpf))
    if not paciente:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=dict_to_xml(
                {"codigo": "PACIENTE_NAO_ENCONTRADO", 
                "mensagem": f"Paciente com CPF {cpf} não encontrado"},
                root_name="erro"
            ),
            headers={"Content-Type": "application/xml"}
        )

def verificar_atendimento_existe(session: Session, id_atendimento: int):
    atendimento = session.get(Atendimento, id_atendimento)
    if not atendimento:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=dict_to_xml(
                {"erro": {"codigo": "ATENDIMENTO_NAO_ENCONTRADO", "mensagem": f"Atendimento {id_atendimento} não encontrado"}},
                root_name="erro"
            ),
            headers={"Content-Type": "application/xml"}
        )
    return atendimento

@router.get("/", response_class=Response)
async def listar_prescricoes(session: Session = Depends(get_session)):
    prescricoes = session.scalars(select(Prescricao).order_by(Prescricao.id_prescricao)).all()
    if not prescricoes:
        return Response(content='<?xml version="1.0" encoding="UTF-8"?>\n<prescricoes/>', media_type="application/xml")
    lista = [prescricao_to_dict(p) for p in prescricoes]
    xml = dict_to_xml({"prescricao": lista}, root_name="prescricoes")
    return Response(content=xml, media_type="application/xml")

@router.get("/{id_prescricao}", response_class=Response)
async def buscar_prescricao(id_prescricao: int, session: Session = Depends(get_session)):
    prescricao = session.get(Prescricao, id_prescricao)
    if not prescricao:
        error_xml = dict_to_xml(
            {"erro": {"codigo": "PRESCRICAO_NAO_ENCONTRADA", "mensagem": f"Prescrição {id_prescricao} não encontrada"}},
            root_name="erro"
        )
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=error_xml, headers={"Content-Type": "application/xml"})
    xml = dict_to_xml({"prescricao": prescricao_to_dict(prescricao)}, root_name="prescricao_encontrada")
    return Response(content=xml, media_type="application/xml")

@router.post("/", response_class=Response, status_code=HTTPStatus.CREATED)
async def criar_prescricao(
    dados: PrescricaoCreate,
    session: Session = Depends(get_session)
):
    # Valida CPF e existência do paciente
    try:
        cpf_limpo = validar_cpf(dados.cpf_paciente)
    except ValueError as e:
        error_xml = dict_to_xml(
            {"erro": {"codigo": "CPF_INVALIDO", "mensagem": str(e)}},
            root_name="erro"
        )
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=error_xml, headers={"Content-Type": "application/xml"})
    verificar_paciente_existe(session, cpf_limpo)

    # Verifica se atendimento existe
    verificar_atendimento_existe(session, dados.id_atendimento)

    # Define data/hora da prescrição (se não informada, usa agora)
    data_presc = dados.data_prescricao or date.today()
    hora_presc = dados.hora_prescricao or datetime.now().time()

    nova_presc = Prescricao(
        id_atendimento=dados.id_atendimento,
        cpf_paciente=cpf_limpo,
        data_prescricao=data_presc,
        hora_prescricao=hora_presc,
        crm_medico=dados.crm_medico,
        codigo_medicamento=dados.codigo_medicamento,
        quantidade=dados.quantidade,
        unidade_medida=dados.unidade_medida,
        observacao=dados.observacao,
        status_estoque=dados.status_estoque
    )
    session.add(nova_presc)
    session.commit()
    session.refresh(nova_presc)

    xml = dict_to_xml({"prescricao": prescricao_to_dict(nova_presc)}, root_name="prescricao_criada")
    return Response(content=xml, media_type="application/xml", status_code=HTTPStatus.CREATED)

@router.put("/{id_prescricao}", response_class=Response)
async def atualizar_prescricao(
    id_prescricao: int,
    dados: PrescricaoCreate,
    session: Session = Depends(get_session)
):
    prescricao = session.get(Prescricao, id_prescricao)
    if not prescricao:
        error_xml = dict_to_xml(
            {"erro": {"codigo": "PRESCRICAO_NAO_ENCONTRADA", "mensagem": f"Prescrição {id_prescricao} não encontrada"}},
            root_name="erro"
        )
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=error_xml, headers={"Content-Type": "application/xml"})

    # Valida CPF se alterado
    if dados.cpf_paciente != prescricao.cpf_paciente:
        try:
            cpf_limpo = validar_cpf(dados.cpf_paciente)
        except ValueError as e:
            error_xml = dict_to_xml(
                {"erro": {"codigo": "CPF_INVALIDO", "mensagem": str(e)}},
                root_name="erro"
            )
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=error_xml, headers={"Content-Type": "application/xml"})
        verificar_paciente_existe(session, cpf_limpo)
        prescricao.cpf_paciente = cpf_limpo

    # Verifica atendimento se alterado
    if dados.id_atendimento != prescricao.id_atendimento:
        verificar_atendimento_existe(session, dados.id_atendimento)
        prescricao.id_atendimento = dados.id_atendimento

    # Atualiza campos
    prescricao.data_prescricao = dados.data_prescricao or prescricao.data_prescricao
    prescricao.hora_prescricao = dados.hora_prescricao or prescricao.hora_prescricao
    prescricao.crm_medico = dados.crm_medico
    prescricao.codigo_medicamento = dados.codigo_medicamento
    prescricao.quantidade = dados.quantidade
    prescricao.unidade_medida = dados.unidade_medida
    prescricao.observacao = dados.observacao
    prescricao.status_estoque = dados.status_estoque

    session.commit()
    session.refresh(prescricao)

    xml = dict_to_xml({"prescricao": prescricao_to_dict(prescricao)}, root_name="prescricao_atualizada")
    return Response(content=xml, media_type="application/xml")

@router.delete("/{id_prescricao}", response_class=Response, status_code=HTTPStatus.OK)
async def deletar_prescricao(id_prescricao: int, session: Session = Depends(get_session)):
    prescricao = session.get(Prescricao, id_prescricao)
    if not prescricao:
        error_xml = dict_to_xml(
            {"erro": {"codigo": "PRESCRICAO_NAO_ENCONTRADA", "mensagem": f"Prescrição {id_prescricao} não encontrada"}},
            root_name="erro"
        )
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=error_xml, headers={"Content-Type": "application/xml"})

    session.delete(prescricao)
    session.commit()

    xml = dict_to_xml(
        {"sucesso": {"mensagem": f"Prescrição {id_prescricao} removida com sucesso"}},
        root_name="resposta"
    )
    return Response(content=xml, media_type="application/xml")