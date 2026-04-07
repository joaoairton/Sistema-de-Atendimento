# routes/pacientes.py — cadastro e consulta de pacientes
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from services.db_service import buscar_paciente, cadastrar_paciente, listar_pacientes
from services.db_service import buscar_status_financeiro
import psycopg2

pac_bp = Blueprint("pacientes", __name__)


@pac_bp.route("/pacientes")
def listar():
    return render_template("pacientes/listar.html", pacientes=listar_pacientes())


@pac_bp.route("/pacientes/novo", methods=["GET", "POST"])
def novo():
    if request.method == "POST":
        cpf   = request.form.get("cpf", "").replace(".", "").replace("-", "")
        nome  = request.form.get("nome", "").strip()
        if len(cpf) != 11 or not cpf.isdigit():
            flash(("erro", "CPF inválido — informe 11 dígitos numéricos."))
            return render_template("pacientes/novo.html")
        if not nome:
            flash(("erro", "Nome é obrigatório."))
            return render_template("pacientes/novo.html")
        try:
            cadastrar_paciente(
                cpf, nome,
                request.form.get("data_nasc") or None,
                request.form.get("telefone") or None,
                request.form.get("email") or None,
            )
            flash(("ok", f"Paciente {nome.upper()} cadastrado."))
            return redirect(url_for("pacientes.listar"))
        except psycopg2.errors.UniqueViolation:
            flash(("erro", "CPF já cadastrado."))
    return render_template("pacientes/novo.html")


@pac_bp.route("/api/paciente/<cpf>")
def api_buscar(cpf):
    """API JSON usada pelo JS da tela de abertura de atendimento."""
    cpf = cpf.replace(".", "").replace("-", "")
    pac = buscar_paciente(cpf)
    if not pac:
        return jsonify({"encontrado": False})
    sf  = buscar_status_financeiro(cpf)
    return jsonify({
        "encontrado": True,
        "nome": pac["nome"],
        "status_financeiro": sf["status_financeiro"] if sf else "NAO_VERIFICADO",
        "permite_atendimento": sf["permite_atendimento"] if sf else "S",
    })
