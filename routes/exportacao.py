# routes/exportacao.py
# Rotas de exportação manual de arquivos por período.

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import date
from app.config import get_db, get_cursor
from services.arquivo_service import (
    exportar_prescricoes, exportar_aberturas, exportar_encerramentos
)

exportacao_bp = Blueprint("exportacao", __name__)


@exportacao_bp.route("/exportar", methods=["GET", "POST"])
def exportar_arquivos():
    hoje = date.today().isoformat()

    if request.method == "POST":
        tipo     = request.form.get("tipo")
        data_ini = request.form.get("data_ini")
        data_fim = request.form.get("data_fim")

        db  = get_db()
        cur = get_cursor(db)
        try:
            nome_arquivo = None

            if tipo == "prescricao":
                cur.execute("""
                    SELECT pr.*, p.nome AS nome_paciente
                    FROM prescricao pr
                    JOIN paciente p ON p.cpf = pr.cpf_paciente
                    WHERE pr.data_prescricao BETWEEN %s AND %s
                    ORDER BY pr.data_prescricao, pr.hora_prescricao
                """, (data_ini, data_fim))
                registros = cur.fetchall()
                if registros:
                    nome_arquivo = exportar_prescricoes(registros, data_ini, data_fim)

            elif tipo == "abertura":
                cur.execute("""
                    SELECT a.*, p.nome AS nome_paciente
                    FROM atendimento a
                    JOIN paciente p ON p.cpf = a.cpf_paciente
                    WHERE a.data_abertura BETWEEN %s AND %s
                    ORDER BY a.data_abertura, a.hora_abertura
                """, (data_ini, data_fim))
                registros = cur.fetchall()
                if registros:
                    nome_arquivo = exportar_aberturas(registros, data_ini, data_fim)

            elif tipo == "encerramento":
                cur.execute("""
                    SELECT a.*, p.nome AS nome_paciente
                    FROM atendimento a
                    JOIN paciente p ON p.cpf = a.cpf_paciente
                    WHERE a.status = 'ENCERRADO'
                      AND a.data_encerramento BETWEEN %s AND %s
                    ORDER BY a.data_encerramento, a.hora_encerramento
                """, (data_ini, data_fim))
                registros = cur.fetchall()
                if registros:
                    nome_arquivo = exportar_encerramentos(registros, data_ini, data_fim)

            if nome_arquivo:
                flash(("sucesso", f"Arquivo gerado: {nome_arquivo}"))
            else:
                flash(("aviso", "Nenhum registro encontrado no periodo selecionado."))

        except Exception as e:
            flash(("erro", f"Erro ao gerar arquivo: {str(e)}"))
        finally:
            cur.close(); db.close()

        return redirect(url_for("exportacao.exportar_arquivos"))

    return render_template("exportar.html", hoje=hoje)


@exportacao_bp.route("/api/exportar-preview")
def exportar_preview():
    """API chamada pelo JavaScript da tela de exportação para mostrar prévia antes de gerar."""
    tipo     = request.args.get("tipo")
    data_ini = request.args.get("data_ini")
    data_fim = request.args.get("data_fim")

    db  = get_db()
    cur = get_cursor(db)
    try:
        if tipo == "prescricao":
            cur.execute("""
                SELECT pr.id_prescricao, p.nome AS nome_paciente,
                       pr.codigo_medicamento, pr.quantidade, pr.unidade_medida,
                       pr.data_prescricao, pr.hora_prescricao
                FROM prescricao pr
                JOIN paciente p ON p.cpf = pr.cpf_paciente
                WHERE pr.data_prescricao BETWEEN %s AND %s
                ORDER BY pr.data_prescricao, pr.hora_prescricao
            """, (data_ini, data_fim))
            rows = cur.fetchall()
            return jsonify({
                "total": len(rows),
                "colunas": ["ID","Paciente","Medicamento","Qtd","Unidade","Data","Hora"],
                "registros": [
                    [r["id_prescricao"], r["nome_paciente"],
                     r["codigo_medicamento"], str(r["quantidade"]),
                     (r["unidade_medida"] or "").strip(),
                     r["data_prescricao"].strftime("%d/%m/%Y"),
                     r["hora_prescricao"].strftime("%H:%M")]
                    for r in rows
                ]
            })

        elif tipo == "abertura":
            cur.execute("""
                SELECT a.id_atendimento, p.nome AS nome_paciente,
                       a.tipo, a.especialidade, a.convenio,
                       a.data_abertura, a.hora_abertura
                FROM atendimento a
                JOIN paciente p ON p.cpf = a.cpf_paciente
                WHERE a.data_abertura BETWEEN %s AND %s
                ORDER BY a.data_abertura, a.hora_abertura
            """, (data_ini, data_fim))
            rows  = cur.fetchall()
            tipos = {"C":"Consulta","R":"Retorno","I":"Internacao","E":"Emergencia"}
            return jsonify({
                "total": len(rows),
                "colunas": ["ID","Paciente","Tipo","Especialidade","Convenio","Data","Hora"],
                "registros": [
                    [r["id_atendimento"], r["nome_paciente"],
                     tipos.get(r["tipo"], r["tipo"]),
                     r["especialidade"] or "—", r["convenio"] or "—",
                     r["data_abertura"].strftime("%d/%m/%Y"),
                     r["hora_abertura"].strftime("%H:%M")]
                    for r in rows
                ]
            })

        elif tipo == "encerramento":
            cur.execute("""
                SELECT a.id_atendimento, p.nome AS nome_paciente,
                       a.cid_principal, a.procedimento,
                       a.qtd_medicamentos, a.valor_procedimentos,
                       a.data_encerramento, a.hora_encerramento
                FROM atendimento a
                JOIN paciente p ON p.cpf = a.cpf_paciente
                WHERE a.status = 'ENCERRADO'
                  AND a.data_encerramento BETWEEN %s AND %s
                ORDER BY a.data_encerramento, a.hora_encerramento
            """, (data_ini, data_fim))
            rows        = cur.fetchall()
            valor_total = sum(float(r["valor_procedimentos"] or 0) for r in rows)
            return jsonify({
                "total": len(rows),
                "valor_total": f"{valor_total:,.2f}".replace(",","X").replace(".",",").replace("X","."),
                "colunas": ["ID","Paciente","CID","Procedimento","Medicamentos","Valor","Data enc."],
                "registros": [
                    [r["id_atendimento"], r["nome_paciente"],
                     r["cid_principal"] or "—", r["procedimento"] or "—",
                     r["qtd_medicamentos"] or 0,
                     f"R$ {float(r['valor_procedimentos'] or 0):,.2f}".replace(",","X").replace(".",",").replace("X","."),
                     r["data_encerramento"].strftime("%d/%m/%Y") if r["data_encerramento"] else "—"]
                    for r in rows
                ]
            })

    except Exception as e:
        return jsonify({"total": 0, "erro": str(e), "colunas": [], "registros": []})
    finally:
        cur.close(); db.close()

    return jsonify({"total": 0, "colunas": [], "registros": []})
