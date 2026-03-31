# routes/atendimentos.py
# Rotas do módulo de atendimentos: listar, abrir, detalhe e encerrar.

from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import date
from app.config import get_db, get_cursor
from utils.formatters import limpar_cpf
from services.arquivo_service import gerar_encerramento

atendimentos_bp = Blueprint("atendimentos", __name__)


@atendimentos_bp.route("/atendimentos")
def listar_atendimentos():
    db  = get_db()
    cur = get_cursor(db)
    try:
        busca       = request.args.get("busca", "")
        data_filtro = request.args.get("data", date.today().isoformat())

        cur.execute("""
            SELECT a.*, p.nome AS nome_paciente
            FROM atendimento a
            JOIN paciente p ON p.cpf = a.cpf_paciente
            WHERE (%s = '' OR p.nome ILIKE %s OR a.cpf_paciente LIKE %s)
              AND (%s = '' OR a.data_abertura = %s::date)
            ORDER BY a.data_abertura DESC, a.hora_abertura DESC
        """, (busca, f"%{busca}%", f"%{busca}%", data_filtro, data_filtro))
        atendimentos = cur.fetchall()
    finally:
        cur.close(); db.close()

    return render_template("atendimentos/listar.html",
        atendimentos=atendimentos, busca=busca, data_filtro=data_filtro)


@atendimentos_bp.route("/atendimentos/novo", methods=["GET", "POST"])
def novo_atendimento():
    if request.method == "POST":
        cpf           = limpar_cpf(request.form["cpf"])
        tipo          = request.form["tipo"]
        crm_medico    = request.form.get("crm_medico", "").strip().upper() or None
        especialidade = request.form.get("especialidade", "").strip().upper() or None
        convenio      = request.form.get("convenio", "").strip().upper() or None
        carteirinha   = request.form.get("carteirinha", "").strip() or None
        observacao    = request.form.get("observacao", "").strip() or None

        db  = get_db()
        cur = get_cursor(db)
        try:
            # Verifica se o paciente existe antes de abrir o atendimento
            cur.execute("SELECT cpf FROM paciente WHERE cpf = %s", (cpf,))
            if not cur.fetchone():
                flash(("erro", "CPF nao encontrado. Cadastre o paciente antes de abrir o atendimento."))
                return redirect(url_for("atendimentos.novo_atendimento"))

            cur.execute("""
                INSERT INTO atendimento
                  (cpf_paciente, data_abertura, hora_abertura, tipo,
                   crm_medico, especialidade, convenio, carteirinha, observacao)
                VALUES (%s, CURRENT_DATE, CURRENT_TIME, %s, %s, %s, %s, %s, %s)
                RETURNING id_atendimento
            """, (cpf, tipo, crm_medico, especialidade, convenio, carteirinha, observacao))

            id_atendimento = cur.fetchone()[0]
            db.commit()
            flash(("sucesso", f"Atendimento #{id_atendimento} aberto com sucesso!"))
            return redirect(url_for("atendimentos.detalhe_atendimento",
                id_atendimento=id_atendimento))
        except Exception as e:
            db.rollback()
            flash(("erro", f"Erro ao abrir atendimento: {str(e)}"))
        finally:
            cur.close(); db.close()

    return render_template("atendimentos/novo.html")


@atendimentos_bp.route("/atendimentos/<int:id_atendimento>")
def detalhe_atendimento(id_atendimento):
    db  = get_db()
    cur = get_cursor(db)
    try:
        cur.execute("""
            SELECT a.*, p.nome AS nome_paciente
            FROM atendimento a JOIN paciente p ON p.cpf = a.cpf_paciente
            WHERE a.id_atendimento = %s
        """, (id_atendimento,))
        atendimento = cur.fetchone()

        if not atendimento:
            flash(("erro", "Atendimento nao encontrado."))
            return redirect(url_for("atendimentos.listar_atendimentos"))

        cur.execute("""
            SELECT * FROM prescricao WHERE id_atendimento = %s
            ORDER BY data_prescricao, hora_prescricao
        """, (id_atendimento,))
        prescricoes = cur.fetchall()
    finally:
        cur.close(); db.close()

    return render_template("atendimentos/detalhe.html",
        atendimento=atendimento, prescricoes=prescricoes)


@atendimentos_bp.route("/atendimentos/<int:id_atendimento>/encerrar", methods=["GET", "POST"])
def encerrar_atendimento(id_atendimento):
    db          = get_db()
    cur         = get_cursor(db)
    atendimento = None
    prescricoes = []
    try:
        cur.execute("""
            SELECT a.*, p.nome AS nome_paciente
            FROM atendimento a JOIN paciente p ON p.cpf = a.cpf_paciente
            WHERE a.id_atendimento = %s AND a.status = 'ABERTO'
        """, (id_atendimento,))
        atendimento = cur.fetchone()

        if not atendimento:
            flash(("erro", "Atendimento nao encontrado ou ja encerrado."))
            return redirect(url_for("atendimentos.listar_atendimentos"))

        cur.execute("SELECT * FROM prescricao WHERE id_atendimento = %s", (id_atendimento,))
        prescricoes = cur.fetchall()

        if request.method == "POST":
            cid_principal       = request.form.get("cid_principal", "").strip().upper()
            procedimento        = request.form.get("procedimento", "").strip()
            valor_str           = request.form.get("valor_procedimentos", "0").replace(",", ".")
            valor_procedimentos = float(valor_str) if valor_str else 0
            observacao          = request.form.get("observacao", "").strip() or None
            qtd_medicamentos    = len(prescricoes)

            cur.execute("""
                UPDATE atendimento SET
                    status              = 'ENCERRADO',
                    data_encerramento   = CURRENT_DATE,
                    hora_encerramento   = CURRENT_TIME,
                    cid_principal       = %s,
                    procedimento        = %s,
                    qtd_medicamentos    = %s,
                    valor_procedimentos = %s,
                    observacao          = %s
                WHERE id_atendimento = %s
                RETURNING data_encerramento, hora_encerramento
            """, (cid_principal, procedimento, qtd_medicamentos,
                  valor_procedimentos, observacao, id_atendimento))

            row      = cur.fetchone()
            data_enc = row[0]
            hora_enc = row[1]
            db.commit()

            nome_arquivo = gerar_encerramento(
                atendimento, cid_principal, procedimento,
                qtd_medicamentos, valor_procedimentos, data_enc, hora_enc
            )

            flash(("sucesso", f"Atendimento #{id_atendimento} encerrado! Arquivo: {nome_arquivo}"))
            return redirect(url_for("atendimentos.detalhe_atendimento",
                id_atendimento=id_atendimento))

    except Exception as e:
        db.rollback()
        flash(("erro", f"Erro ao encerrar: {str(e)}"))
    finally:
        cur.close(); db.close()

    return render_template("atendimentos/encerrar.html",
        atendimento=atendimento, prescricoes=prescricoes)
