# routes/pacientes.py
# Rotas do módulo de pacientes.
# Cada função lê o formulário, chama o banco e renderiza o template.

from flask import Blueprint, render_template, request, redirect, url_for, flash
import psycopg2
from config import get_db, get_cursor
from utils.formatters import limpar_cpf, limpar_telefone

pacientes_bp = Blueprint("pacientes", __name__)


def validar_paciente(cpf, nome):
    """
    Valida os dois campos obrigatórios do cadastro de paciente.
    Retorna uma lista de erros — se vazia, os dados são válidos.
    """
    erros = []

    # CPF obrigatório e com exatamente 11 dígitos numéricos
    if not cpf:
        erros.append("CPF é obrigatório.")
    elif not cpf.isdigit():
        erros.append("CPF deve conter apenas números.")
    elif len(cpf) != 11:
        erros.append(f"CPF deve ter 11 dígitos. Você informou {len(cpf)}.")

    # Nome obrigatório e não pode ser só espaços
    if not nome or not nome.strip():
        erros.append("Nome é obrigatório.")

    return erros


@pacientes_bp.route("/pacientes")
def listar_pacientes():
    db  = get_db()
    cur = get_cursor(db)
    try:
        busca = request.args.get("busca", "")
        if busca:
            cur.execute("""
                SELECT * FROM paciente
                WHERE nome ILIKE %s OR cpf LIKE %s
                ORDER BY nome
            """, (f"%{busca}%", f"%{busca}%"))
        else:
            cur.execute("SELECT * FROM paciente ORDER BY nome")
        pacientes = cur.fetchall()
    finally:
        cur.close(); db.close()

    return render_template("pacientes/listar.html", pacientes=pacientes, busca=busca)


@pacientes_bp.route("/pacientes/novo", methods=["GET", "POST"])
def novo_paciente():
    if request.method == "POST":
        cpf       = limpar_cpf(request.form.get("cpf", ""))
        nome      = request.form.get("nome", "").strip().upper()
        data_nasc = request.form.get("data_nasc") or None
        telefone  = limpar_telefone(request.form.get("telefone", "")) or None
        email     = request.form.get("email", "").strip().lower() or None

        # Valida campos obrigatórios antes de qualquer acesso ao banco
        erros = validar_paciente(cpf, nome)
        if erros:
            for erro in erros:
                flash(("erro", erro))
            return render_template("pacientes/novo.html",
                form={"cpf": request.form.get("cpf",""),
                      "nome": request.form.get("nome",""),
                      "data_nasc": request.form.get("data_nasc",""),
                      "telefone": request.form.get("telefone",""),
                      "email": request.form.get("email","")})

        db  = get_db()
        cur = get_cursor(db)
        try:
            cur.execute("""
                INSERT INTO paciente (cpf, nome, data_nasc, telefone, email)
                VALUES (%s, %s, %s, %s, %s)
            """, (cpf, nome, data_nasc, telefone, email))
            db.commit()
            flash(("sucesso", f"Paciente {nome} cadastrado com sucesso!"))
            return redirect(url_for("pacientes.listar_pacientes"))
        except psycopg2.errors.UniqueViolation:
            db.rollback()
            flash(("erro", "CPF ja cadastrado no sistema."))
            return render_template("pacientes/novo.html",
                form={"cpf": request.form.get("cpf",""),
                      "nome": nome,
                      "data_nasc": request.form.get("data_nasc",""),
                      "telefone": request.form.get("telefone",""),
                      "email": request.form.get("email","")})
        except Exception as e:
            db.rollback()
            flash(("erro", f"Erro ao cadastrar: {str(e)}"))
        finally:
            cur.close(); db.close()

    return render_template("pacientes/novo.html", form={})


@pacientes_bp.route("/pacientes/<cpf>")
def detalhe_paciente(cpf):
    db  = get_db()
    cur = get_cursor(db)
    try:
        cur.execute("SELECT * FROM paciente WHERE cpf = %s", (cpf,))
        paciente = cur.fetchone()

        if not paciente:
            flash(("erro", "Paciente nao encontrado."))
            return redirect(url_for("pacientes.listar_pacientes"))

        cur.execute("""
            SELECT * FROM atendimento
            WHERE cpf_paciente = %s
            ORDER BY data_abertura DESC, hora_abertura DESC
        """, (cpf,))
        atendimentos = cur.fetchall()
    finally:
        cur.close(); db.close()

    return render_template("pacientes/detalhe.html",
        paciente=paciente, atendimentos=atendimentos)


@pacientes_bp.route("/pacientes/<cpf>/editar", methods=["GET", "POST"])
def editar_paciente(cpf):
    db  = get_db()
    cur = get_cursor(db)
    try:
        cur.execute("SELECT * FROM paciente WHERE cpf = %s", (cpf,))
        paciente = cur.fetchone()

        if request.method == "POST":
            nome      = request.form.get("nome", "").strip().upper()
            data_nasc = request.form.get("data_nasc") or None
            telefone  = limpar_telefone(request.form.get("telefone", "")) or None
            email     = request.form.get("email", "").strip().lower() or None

            # Valida nome antes de atualizar (CPF não pode ser alterado)
            if not nome:
                flash(("erro", "Nome é obrigatório."))
                return render_template("pacientes/editar.html", paciente=paciente)

            cur.execute("""
                UPDATE paciente SET nome=%s, data_nasc=%s, telefone=%s, email=%s
                WHERE cpf=%s
            """, (nome, data_nasc, telefone, email, cpf))
            db.commit()
            flash(("sucesso", "Dados atualizados com sucesso!"))
            return redirect(url_for("pacientes.detalhe_paciente", cpf=cpf))

    except Exception as e:
        db.rollback()
        flash(("erro", f"Erro ao atualizar: {str(e)}"))
    finally:
        cur.close(); db.close()

    return render_template("pacientes/editar.html", paciente=paciente)
