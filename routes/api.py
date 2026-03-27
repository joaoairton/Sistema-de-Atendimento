# routes/api.py
# APIs internas em JSON — chamadas pelo JavaScript das telas via fetch().
# Não renderizam HTML.

from flask import Blueprint, jsonify
from config import get_db, get_cursor
from utils.formatters import limpar_cpf

api_bp = Blueprint("api", __name__)


@api_bp.route("/api/verificar-cpf/<cpf>")
def verificar_cpf(cpf):
    """
    Verifica em tempo real se um CPF já está cadastrado.
    Usado no formulário de cadastro de paciente.
    Retorna: { existe: bool, nome: str }
    """
    cpf = limpar_cpf(cpf)
    db  = get_db()
    cur = db.cursor()
    try:
        cur.execute("SELECT nome FROM paciente WHERE cpf = %s", (cpf,))
        resultado = cur.fetchone()
    finally:
        cur.close(); db.close()

    if resultado:
        return jsonify({"existe": True, "nome": resultado[0]})
    return jsonify({"existe": False})


@api_bp.route("/api/paciente-status/<cpf>")
def paciente_status(cpf):
    """
    Retorna dados do paciente e seu status financeiro mais recente.
    Usado na tela de abertura de atendimento.
    O status vem da tabela status_financeiro, populada ao importar
    o arquivo do Sistema Financeiro.
    Retorna: { existe: bool, nome: str, status_financeiro: str, ... }
    """
    cpf = limpar_cpf(cpf)
    db  = get_db()
    cur = get_cursor(db)
    try:
        cur.execute("SELECT cpf, nome FROM paciente WHERE cpf = %s", (cpf,))
        paciente = cur.fetchone()

        if not paciente:
            return jsonify({"existe": False})

        status_fin     = "NAO_VERIFICADO"
        qtd_pendencias = 0
        valor_pendente = 0

        try:
            cur.execute("""
                SELECT status_financeiro, qtd_pendencias, valor_total_pendente
                FROM status_financeiro
                WHERE cpf_paciente = %s
                ORDER BY data_geracao DESC LIMIT 1
            """, (cpf,))
            sf = cur.fetchone()
            if sf:
                status_fin     = sf["status_financeiro"]
                qtd_pendencias = sf["qtd_pendencias"]
                valor_pendente = sf["valor_total_pendente"]
        except Exception:
            # Tabela ainda não criada — comportamento esperado na fase atual
            pass

    finally:
        cur.close(); db.close()

    return jsonify({
        "existe":            True,
        "nome":              paciente["nome"],
        "status_financeiro": status_fin,
        "qtd_pendencias":    qtd_pendencias,
        "valor_pendente":    valor_pendente
    })
