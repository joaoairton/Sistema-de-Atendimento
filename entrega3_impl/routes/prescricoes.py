# routes/prescricoes.py
# Fluxo com o Estoque em duas etapas:
#   1. Prescrever → gera CONSULTA.xml → Estoque responde disponibilidade
#   2. Confirmar reserva → gera RESERVA.xml → Estoque efetiva a reserva
#
# A finalização do atendimento é bloqueada se houver prescrições
# disponíveis sem reserva confirmada.

from flask import Blueprint, render_template, request, redirect, url_for, flash
from services import db_service as db
from services import xml_service as xml
import config

pres_bp = Blueprint("prescricoes", __name__)


@pres_bp.route("/atendimentos/<int:id_atend>/prescricao", methods=["GET", "POST"])
def nova(id_atend):
    """
    Etapa 1: médico registra a prescrição.
    Sistema gera XML de CONSULTA para o Estoque verificar disponibilidade.
    """
    atend = db.buscar_atendimento(id_atend)
    if not atend or atend["status"] != "ABERTO":
        flash(("erro", "Atendimento não encontrado ou já finalizado."))
        return redirect(url_for("atendimentos.listar"))

    prescricoes = db.buscar_prescricoes_atendimento(id_atend)

    if request.method == "POST":
        try:
            codigo_med = int(request.form.get("codigo_med", 0))
            quantidade = float(request.form.get("quantidade", "0").replace(",", "."))
            unidade    = request.form.get("unidade", "COMP")
            crm        = request.form.get("crm", "").strip() or atend["crm_medico"] or ""
            instrucoes = request.form.get("instrucoes", "").strip() or None

            # 1. Grava prescrição no banco
            id_pres, _, _ = db.registrar_prescricao(
                id_atend, atend["cpf_paciente"], crm,
                codigo_med, quantidade, unidade, instrucoes
            )

            # 2. Busca registro completo (data/hora do banco)
            prescricao = db.buscar_prescricao(id_pres)

            # 3. Gera XML de CONSULTA no formato do Estoque (consulta.xsd)
            xml_bytes = xml.gerar_xml_consulta_estoque([dict(prescricao)])
            nome      = xml.nome_consulta(id_atend)
            xml.salvar_xml(xml_bytes, nome, config.XML_SAIDA)

            # 4. Valida contra consulta.xsd do Estoque
            valido, erro = xml.validar_xml(xml_bytes, config.XSD_ESTOQUE_CONSULTA)

            if valido:
                flash(("ok",
                    f"Prescrição #{id_pres} registrada. "
                    f"XML de consulta gerado: {nome}. "
                    f"Aguardando resposta do Estoque."))
            else:
                flash(("aviso", f"XML gerado com erro de validação: {erro}"))

        except Exception as e:
            flash(("erro", f"Erro ao registrar prescrição: {e}"))

        return redirect(url_for("prescricoes.nova", id_atend=id_atend))

    return render_template("prescricoes/nova.html",
                           atend=atend, prescricoes=prescricoes)


@pres_bp.route("/prescricoes/<int:id_pres>/reservar", methods=["POST"])
def confirmar_reserva(id_pres):
    """
    Etapa 2: após importar a resposta do Estoque e verificar disponibilidade,
    o usuário confirma a reserva do medicamento.
    Sistema gera XML de RESERVA no formato do Estoque (reserva.xsd).
    """
    prescricao = db.buscar_prescricao(id_pres)
    if not prescricao:
        flash(("erro", "Prescrição não encontrada."))
        return redirect(url_for("atendimentos.listar"))

    try:
        # 1. Gera XML de RESERVA
        xml_bytes = xml.gerar_xml_reserva_estoque([dict(prescricao)])
        nome      = xml.nome_reserva(prescricao["id_atendimento"])
        xml.salvar_xml(xml_bytes, nome, config.XML_SAIDA)

        # 2. Valida contra reserva.xsd do Estoque
        valido, erro = xml.validar_xml(xml_bytes, config.XSD_ESTOQUE_RESERVA)

        if valido:
            # 3. Marca reserva como confirmada no banco
            db.confirmar_reserva(id_pres)
            flash(("ok", f"Reserva confirmada. XML gerado: {nome}"))
        else:
            flash(("aviso", f"XML de reserva gerado com erro: {erro}"))

    except Exception as e:
        flash(("erro", f"Erro ao confirmar reserva: {e}"))

    return redirect(url_for("atendimentos.detalhe",
                            id=prescricao["id_atendimento"]))
