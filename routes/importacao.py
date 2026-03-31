# routes/importacao.py
# Rotas de importação dos arquivos recebidos do Estoque e do Financeiro.

from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.config import get_db, get_cursor
from services.importacao_service import (
    importar_retorno_estoque,
    importar_status_financeiro
)

importacao_bp = Blueprint("importacao", __name__)


@importacao_bp.route("/importar", methods=["GET", "POST"])
def importar_arquivos():
    if request.method == "POST":
        tipo    = request.form.get("tipo")
        arquivo = request.files.get("arquivo")

        if not arquivo or arquivo.filename == "":
            flash(("erro", "Nenhum arquivo selecionado."))
            return redirect(url_for("importacao.importar_arquivos"))

        if not arquivo.filename.endswith(".txt"):
            flash(("erro", "Apenas arquivos .txt são aceitos."))
            return redirect(url_for("importacao.importar_arquivos"))

        conteudo = arquivo.read().decode("utf-8")

        db  = get_db()
        cur = get_cursor(db)
        try:
            if tipo == "estoque":
                resultado = importar_retorno_estoque(conteudo, cur)
                db.commit()
                flash(("sucesso",
                    f"Estoque importado: {resultado['processados']} registro(s) processado(s)."))

            elif tipo == "financeiro":
                resultado = importar_status_financeiro(conteudo, cur)
                db.commit()
                flash(("sucesso",
                    f"Financeiro importado: {resultado['processados']} paciente(s) atualizado(s)."))

            else:
                flash(("erro", "Tipo de arquivo inválido."))

        except ValueError as e:
            # Erros de validação do arquivo (hash, estrutura, etc.)
            db.rollback()
            flash(("erro", str(e)))
        except Exception as e:
            db.rollback()
            flash(("erro", f"Erro ao importar: {str(e)}"))
        finally:
            cur.close(); db.close()

        return redirect(url_for("importacao.importar_arquivos"))

    # GET — busca últimas importações para exibir na tela
    db  = get_db()
    cur = get_cursor(db)
    try:
        cur.execute("""
            SELECT re.id, re.id_prescricao, re.codigo_medicamento,
                   re.disponivel, re.observacao, re.data_importacao,
                   p.nome AS nome_paciente
            FROM retorno_estoque re
            JOIN prescricao pr ON pr.id_prescricao = re.id_prescricao
            JOIN paciente p    ON p.cpf = pr.cpf_paciente
            ORDER BY re.data_importacao DESC
            LIMIT 20
        """)
        retornos_estoque = cur.fetchall()

        cur.execute("""
            SELECT sf.id, sf.cpf_paciente, sf.status_financeiro,
                   sf.qtd_pendencias, sf.valor_total_pendente,
                   sf.permite_atendimento, sf.data_geracao,
                   p.nome AS nome_paciente
            FROM status_financeiro sf
            JOIN paciente p ON p.cpf = sf.cpf_paciente
            ORDER BY sf.data_geracao DESC, sf.id DESC
            LIMIT 20
        """)
        status_fin = cur.fetchall()
    finally:
        cur.close(); db.close()

    return render_template("importar.html",
        retornos_estoque=retornos_estoque,
        status_fin=status_fin)
