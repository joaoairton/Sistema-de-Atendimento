# routes/prescricoes.py
# Rotas do módulo de prescrições: listar e nova prescrição.

from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import date
from app.config import get_db, get_cursor
from services.arquivo_service import gerar_prescricao

prescricoes_bp = Blueprint("prescricoes", __name__)


@prescricoes_bp.route("/prescricoes")
def listar_prescricoes():
    db  = get_db()
    cur = get_cursor(db)
    try:
        data_filtro = request.args.get("data", date.today().isoformat())
        cur.execute("""
            SELECT pr.*, p.nome AS nome_paciente
            FROM prescricao pr
            JOIN paciente p ON p.cpf = pr.cpf_paciente
            WHERE (%s = '' OR pr.data_prescricao = %s::date)
            ORDER BY pr.data_prescricao DESC, pr.hora_prescricao DESC
        """, (data_filtro, data_filtro))
        prescricoes = cur.fetchall()
    finally:
        cur.close(); db.close()

    return render_template("prescricoes/listar.html",
        prescricoes=prescricoes, data_filtro=data_filtro)


@prescricoes_bp.route("/atendimentos/<int:id_atendimento>/prescricao/nova",
                      methods=["GET", "POST"])
def nova_prescricao(id_atendimento):
    db          = get_db()
    cur         = get_cursor(db)
    atendimento = None
    prescricoes = []
    try:
        # Só aceita atendimentos ABERTOS
        cur.execute("""
            SELECT a.*, p.nome AS nome_paciente
            FROM atendimento a JOIN paciente p ON p.cpf = a.cpf_paciente
            WHERE a.id_atendimento = %s AND a.status = 'ABERTO'
        """, (id_atendimento,))
        atendimento = cur.fetchone()

        if not atendimento:
            flash(("erro", "Atendimento nao encontrado ou ja encerrado."))
            return redirect(url_for("atendimentos.listar_atendimentos"))

        cur.execute("""
            SELECT * FROM prescricao WHERE id_atendimento = %s
            ORDER BY data_prescricao, hora_prescricao
        """, (id_atendimento,))
        prescricoes = cur.fetchall()

        if request.method == "POST":
            crm_medico         = request.form.get("crm_medico", "").strip().upper() or None
            codigo_medicamento = request.form.get("codigo_medicamento")
            quantidade         = request.form.get("quantidade")
            unidade_medida     = request.form.get("unidade_medida", "").strip()
            observacao         = request.form.get("observacao", "").strip() or None

            cur.execute("""
                INSERT INTO prescricao
                  (id_atendimento, cpf_paciente, data_prescricao, hora_prescricao,
                   crm_medico, codigo_medicamento, quantidade, unidade_medida, observacao)
                VALUES (%s, %s, CURRENT_DATE, CURRENT_TIME, %s, %s, %s, %s, %s)
                RETURNING id_prescricao, data_prescricao, hora_prescricao
            """, (id_atendimento, atendimento["cpf_paciente"],
                  crm_medico, codigo_medicamento, quantidade, unidade_medida, observacao))

            row             = cur.fetchone()
            id_prescricao   = row[0]
            data_prescricao = row[1]
            hora_prescricao = row[2]
            db.commit()

            # Gera o arquivo apenas após o commit bem-sucedido
            nome_arquivo = gerar_prescricao(
                id_prescricao, atendimento, crm_medico,
                codigo_medicamento, quantidade, unidade_medida, observacao,
                data_prescricao, hora_prescricao
            )

            flash(("sucesso", f"Prescricao #{id_prescricao} registrada! Arquivo: {nome_arquivo}"))
            return redirect(url_for("prescricoes.nova_prescricao",
                id_atendimento=id_atendimento))

    except Exception as e:
        db.rollback()
        flash(("erro", f"Erro ao registrar prescricao: {str(e)}"))
    finally:
        cur.close(); db.close()

    return render_template("prescricoes/novo.html",
        atendimento=atendimento, prescricoes=prescricoes)
