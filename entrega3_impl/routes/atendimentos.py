# routes/atendimentos.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from services import db_service as db
from services import xml_service as xml
import config

atend_bp = Blueprint("atendimentos", __name__)


@atend_bp.route("/atendimentos")
def listar():
    return render_template("atendimentos/listar.html",
                           atendimentos=db.listar_atendimentos())


@atend_bp.route("/atendimentos/novo", methods=["GET", "POST"])
def novo():
    if request.method == "POST":
        cpf = request.form.get("cpf", "").replace(".", "").replace("-", "")
        if not db.buscar_paciente(cpf):
            flash(("erro", "Paciente não encontrado. Cadastre-o primeiro."))
            return render_template("atendimentos/novo.html")
        id_atend = db.abrir_atendimento(
            cpf=cpf,
            tipo=request.form.get("tipo"),
            crm=request.form.get("crm") or None,
            convenio=request.form.get("convenio") or None,
            carteirinha=request.form.get("carteirinha") or None,
        )
        flash(("ok", f"Atendimento #{id_atend} aberto."))
        return redirect(url_for("atendimentos.detalhe", id=id_atend))
    return render_template("atendimentos/novo.html")


@atend_bp.route("/atendimentos/<int:id>")
def detalhe(id):
    atend = db.buscar_atendimento(id)
    if not atend:
        flash(("erro", "Atendimento não encontrado."))
        return redirect(url_for("atendimentos.listar"))
    prescricoes = db.buscar_prescricoes_atendimento(id)

    # Verifica se há prescrições bloqueando a finalização
    pendentes_reserva = []
    if atend["status"] == "ABERTO":
        pendentes_reserva = db.prescricoes_pendentes_reserva(id)

    return render_template("atendimentos/detalhe.html",
                           atend=atend,
                           prescricoes=prescricoes,
                           pendentes_reserva=pendentes_reserva)


@atend_bp.route("/atendimentos/<int:id>/finalizar", methods=["GET", "POST"])
def finalizar(id):
    atend = db.buscar_atendimento(id)
    if not atend or atend["status"] != "ABERTO":
        flash(("erro", "Atendimento não encontrado ou já finalizado."))
        return redirect(url_for("atendimentos.listar"))

    prescricoes = db.buscar_prescricoes_atendimento(id)

    # Bloqueia se houver prescrições com medicamento disponível
    # mas reserva ainda não confirmada
    pendentes = db.prescricoes_pendentes_reserva(id)
    if pendentes:
        msgs = []
        sem_resposta  = [p for p in pendentes if p["disponivel"] is None]
        sem_reserva   = [p for p in pendentes if p["disponivel"] is True
                         and p["reserva_confirmada"] is False]
        if sem_resposta:
            codigos = ", ".join(str(p["codigo_med"]) for p in sem_resposta)
            msgs.append(f"{len(sem_resposta)} prescrição(ões) aguardando resposta do Estoque (cód: {codigos})")
        if sem_reserva:
            codigos = ", ".join(str(p["codigo_med"]) for p in sem_reserva)
            msgs.append(f"{len(sem_reserva)} prescrição(ões) com reserva não confirmada (cód: {codigos})")
        flash(("erro", "Não é possível finalizar: " + " | ".join(msgs)))
        return redirect(url_for("atendimentos.detalhe", id=id))

    if request.method == "POST":
        cid         = request.form.get("cid", "").strip().upper()
        codigo_tuss = request.form.get("codigo_tuss", "").strip()
        valor       = float(request.form.get("valor_total", "0").replace(",", ".") or 0)
        obs         = request.form.get("observacoes", "").strip() or None

        # 1. Finaliza no banco
        if not db.finalizar_atendimento(id, cid, codigo_tuss, valor, obs):
            flash(("erro", "Falha ao finalizar atendimento."))
            return redirect(url_for("atendimentos.detalhe", id=id))

        # Recarrega com data/hora do banco
        atend = db.buscar_atendimento(id)

        # 2. Gera XML de finalização para o Financeiro
        xml_bytes = xml.gerar_xml_finalizacao(
            dict(atend), [dict(p) for p in prescricoes]
        )
        nome  = xml.nome_finalizacao(id)
        xml.salvar_xml(xml_bytes, nome, config.XML_SAIDA)

        # 3. Valida contra finalizacao.xsd
        valido, erro = xml.validar_xml(xml_bytes, config.XSD_FINALIZACAO)

        if valido:
            flash(("ok", f"Atendimento finalizado. XML de finalização válido: {nome}"))
        else:
            flash(("aviso", f"XML gerado com erro de validação: {erro}"))

        return redirect(url_for("atendimentos.detalhe", id=id))

    return render_template("atendimentos/finalizar.html",
                           atend=atend, prescricoes=prescricoes)
