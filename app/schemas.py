from pydantic import BaseModel, field_validator, EmailStr
from datetime import date, time
from typing import Optional
import re
from utils.formatters import limpar_cpf, limpar_telefone, erro_xml

# Definimos o esquema dos dados
class PacienteCreate(BaseModel):
    cpf: str
    nome: str
    data_nasc: date 
    telefone: str
    email: EmailStr
    
    @field_validator('cpf')
    @classmethod
    def validar_e_limpar_cpf(cls, v):
        # 1. Limpa usando sua função utilitária
        cpf_limpo = limpar_cpf(v)
        
        # 2. Valida a regra de negócio
        if len(cpf_limpo) != 11:
            # IMPORTANTE: O Pydantic espera um ValueError ou AssertionError
            # Passamos a string XML dentro da mensagem do erro
            raise ValueError(erro_xml("cpf", "CPF deve conter 11 dígitos."))
            
        return cpf_limpo

    @field_validator('telefone')
    @classmethod
    def validar_e_limpar_telefone(cls, v):
        tel_limpo = limpar_telefone(v)
        if not (10 <= len(tel_limpo) <= 11):
            raise ValueError(erro_xml("telefone", "Telefone deve ter 10 ou 11 dígitos."))
        return tel_limpo

class AtendimentoCreate(BaseModel):
    cpf_paciente: str
    tipo: Optional[str] = None
    crm_medico: Optional[str] = None
    especialidade: Optional[str] = None
    convenio: Optional[str] = None
    carteirinha: Optional[str] = None
    status: Optional[str] = None
    observacao: Optional[str] = None
    data_encerramento: Optional[date] = None
    hora_encerramento: Optional[time] = None
    cid_principal: Optional[str] = None
    procedimento: Optional[str] = None
    qtd_medicamentos: Optional[int] = None
    valor_procedimentos: Optional[float] = None

    @field_validator('cpf_paciente')
    def validar_cpf(cls, v):
        # Remove caracteres não numéricos
        cpf_limpo = re.sub(r'[^0-9]', '', v)
        if len(cpf_limpo) != 11:
            raise ValueError('CPF deve conter 11 dígitos')
        # Aqui você pode chamar a validação de dígitos (opcional)
        return cpf_limpo

    @field_validator('status')
    def validar_status(cls, v):
        if v and v not in ['ABERTO', 'EM_ATENDIMENTO', 'ENCERRADO', 'CANCELADO']:
            raise ValueError('Status inválido')
        return v

class PrescricaoCreate(BaseModel):
    id_atendimento: int
    cpf_paciente: str
    data_prescricao: Optional[date] = None
    hora_prescricao: Optional[time] = None
    crm_medico: Optional[str] = None
    codigo_medicamento: Optional[int] = None
    quantidade: Optional[float] = None
    unidade_medida: Optional[str] = None
    observacao: Optional[str] = None
    status_estoque: Optional[str] = None

    @field_validator('cpf_paciente')
    def validar_cpf(cls, v):
        cpf_limpo = re.sub(r'[^0-9]', '', v)
        if len(cpf_limpo) != 11:
            raise ValueError('CPF deve conter 11 dígitos')
        return cpf_limpo

    @field_validator('unidade_medida')
    def validar_unidade(cls, v):
        if v and v not in ['mg', 'g', 'ml', 'comp', 'amp', 'gotas']:
            raise ValueError('Unidade de medida inválida')
        return v

    @field_validator('status_estoque')
    def validar_status(cls, v):
        if v and v not in ['DISPONIVEL', 'INDISPONIVEL', 'EM_FALTA']:
            raise ValueError('Status de estoque inválido')
        return v