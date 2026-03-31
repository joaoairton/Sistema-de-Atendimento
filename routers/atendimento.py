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
    """Cria um novo atendimento"""
    # Valida CPF
    cpf_limpo = limpar_cpf(dados.cpf_paciente)
    verificar_paciente_existe(session, cpf_limpo)

    # Cria objeto
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
        # Preenche data/hora abertura automaticamente
        data_abertura=date.today(),
        hora_abertura=datetime.now().time()
    )
    session.add(novo)
    session.commit()
    session.refresh(novo)

    xml = dict_to_xml({"atendimento": atendimento_to_dict(novo)}, root_name="atendimento_criado")
    return Response(content=xml, media_type="application/xml", status_code=HTTPStatus.CREATED)

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