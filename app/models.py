from datetime import date, datetime, time
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Time,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, registry, relationship

table_registry = registry()


@table_registry.mapped_as_dataclass
class Paciente:
    __tablename__ = "paciente"

    cpf: Mapped[str] = mapped_column(String(11), primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    data_nasc: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    telefone: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    data_cadastro: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), init=False
    )

    # Relacionamentos
    status_financeiros: Mapped[List["StatusFinanceiro"]] = relationship(
        back_populates="paciente", init=False, default_factory=list
    )
    atendimentos: Mapped[List["Atendimento"]] = relationship(
        back_populates="paciente", init=False, default_factory=list
    )


@table_registry.mapped_as_dataclass
class StatusFinanceiro:
    __tablename__ = "status_financeiro"

    id: Mapped[int] = mapped_column(BigInteger, autoincrement=True, primary_key=True)
    cpf_paciente: Mapped[str] = mapped_column(
        String(11), ForeignKey("paciente.cpf"), nullable=False
    )
    status_financeiro: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    qtd_pendencias: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    valor_total_pendente: Mapped[Optional[float]] = mapped_column(
        Numeric(11, 2), nullable=True
    )
    data_vencimento_mais_antiga: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True
    )
    permite_atendimento: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    observacao: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    data_geracao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    hora_geracao: Mapped[Optional[time]] = mapped_column(Time, nullable=True)

    # Relacionamento
    paciente: Mapped["Paciente"] = relationship(back_populates="status_financeiros")


@table_registry.mapped_as_dataclass
class Atendimento:
    __tablename__ = "atendimento"

    id_atendimento: Mapped[int] = mapped_column(
        BigInteger, autoincrement=True, primary_key=True
    )
    cpf_paciente: Mapped[str] = mapped_column(
        String(11), ForeignKey("paciente.cpf"), nullable=False
    )
    data_abertura: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    hora_abertura: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    tipo: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    crm_medico: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    especialidade: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    convenio: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    carteirinha: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    observacao: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    data_encerramento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    hora_encerramento: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    cid_principal: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    procedimento: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    qtd_medicamentos: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    valor_procedimentos: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )

    # Relacionamentos
    paciente: Mapped["Paciente"] = relationship(back_populates="atendimentos")
    prescricoes: Mapped[List["Prescricao"]] = relationship(
        back_populates="atendimento", init=False, default_factory=list
    )


@table_registry.mapped_as_dataclass
class Prescricao:
    __tablename__ = "prescricao"

    id_prescricao: Mapped[int] = mapped_column(
        BigInteger, autoincrement=True, primary_key=True
    )
    id_atendimento: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("atendimento.id_atendimento"), nullable=False
    )
    cpf_paciente: Mapped[str] = mapped_column(
        String(11), ForeignKey("paciente.cpf"), nullable=False
    )
    data_prescricao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    hora_prescricao: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    crm_medico: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    codigo_medicamento: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    quantidade: Mapped[Optional[float]] = mapped_column(Numeric(5, 3), nullable=True)
    unidade_medida: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    observacao: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status_estoque: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)

    # Relacionamentos
    atendimento: Mapped["Atendimento"] = relationship(back_populates="prescricoes")
    paciente: Mapped["Paciente"] = relationship()
    retornos_estoque: Mapped[List["RetornoEstoque"]] = relationship(
        back_populates="prescricao", init=False, default_factory=list
    )


@table_registry.mapped_as_dataclass
class RetornoEstoque:
    __tablename__ = "retorno_estoque"

    id: Mapped[int] = mapped_column(BigInteger, autoincrement=True, primary_key=True)
    id_prescricao: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("prescricao.id_prescricao"), nullable=False
    )
    codigo_medicamento: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    disponivel: Mapped[Optional[float]] = mapped_column(Numeric(1), nullable=True)
    observacao: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    data_importacao: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), init=False
    )

    # Relacionamento
    prescricao: Mapped["Prescricao"] = relationship(back_populates="retornos_estoque")