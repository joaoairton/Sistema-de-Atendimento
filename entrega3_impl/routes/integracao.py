# routes/integracao.py
# Listagem dos XMLs gerados e importação de XMLs externos.
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from services import db_service as db
from services import xml_service as xml
import config, os, glob

integ_bp = Blueprint("integracao", __name__)


# ─── XMLs gerados (saída) ─────────────────────────────────────────────────────

@integ_bp.route("/xmls")
def listar_xmls():
    arquivos = sorted(
        glob.glob(os.path.join(config.XML_SAIDA, "*.xml")),
        reverse=True
    )
    xmls = []
    for caminho in arquivos:
        nome = os.path.basename(caminho)
        if nome.startswith("CONSULTA"):
            tipo = "CONSULTA → Estoque"
        elif nome.startswith("RESERVA"):
            tipo = "RESERVA → Estoque"
        elif nome.startswith("FINALIZACAO"):
            tipo = "FINALIZAÇÃO → Financeiro"
        else:
            tipo = "XML"
        xmls.append({
            "nome":       nome,
            "tipo":       tipo,
            "tamanho":    os.path.getsize(caminho),
        })
    return render_template("integracao/xmls.html", xmls=xmls)


@integ_bp.route("/xmls/<nome>")
def ver_xml(nome):
    caminho = os.path.join(config.XML_SAIDA, nome)
    if not os.path.exists(caminho):
        flash(("erro", "Arquivo não encontrado."))
        return redirect(url_for("integracao.listar_xmls"))
    with open(caminho, encoding="utf-8") as f:
        conteudo = f.read()
    return render_template("integracao/ver_xml.html", nome=nome, conteudo=conteudo)


@integ_bp.route("/xmls/<nome>/download")
def download_xml(nome):
    caminho = os.path.join(config.XML_SAIDA, nome)
    if not os.path.exists(caminho):
        flash(("erro", "Arquivo não encontrado."))
        return redirect(url_for("integracao.listar_xmls"))
    with open(caminho, encoding="utf-8") as f:
        conteudo = f.read()
    return Response(conteudo, mimetype="application/xml",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})


# ─── Importação de XMLs externos ──────────────────────────────────────────────

@integ_bp.route("/importar", methods=["GET", "POST"])
def importar():
    if request.method == "POST":
        origem  = request.form.get("origem")
        arquivo = request.files.get("arquivo")

        if not arquivo or arquivo.filename == "":
            flash(("erro", "Nenhum arquivo selecionado."))
            return redirect(url_for("integracao.importar"))

        xml_bytes = arquivo.read()
        nome_arq  = arquivo.filename

        # Salva em xml_entrada/ antes de qualquer processamento
        xml.salvar_xml(xml_bytes, nome_arq, config.XML_ENTRADA)

        # Roteia para o processador correto
        if origem == "ESTOQUE":
            _importar_estoque(xml_bytes)
        elif origem == "FINANCEIRO":
            _importar_financeiro(xml_bytes)
        else:
            flash(("erro", "Origem inválida."))

        return redirect(url_for("integracao.importar"))

    return render_template("integracao/importar.html")


# ─── Processadores ────────────────────────────────────────────────────────────

def _importar_estoque(xml_bytes):
    """
    Importa resposta.xml do Estoque.
    Valida contra resposta.xsd, parseia e grava em retorno_estoque.

    LIMITAÇÃO DO SCHEMA DO ESTOQUE:
    O resposta.xsd não inclui <prescricao> — apenas <codigo_medicamento>.
    O sistema associa a resposta ao código do medicamento nas prescrições
    com retorno pendente no banco.
    """
    # Valida contra resposta.xsd do Estoque
    valido, erro = xml.validar_xml(xml_bytes, config.XSD_ESTOQUE_RESPOSTA)
    if not valido:
        flash(("erro", f"XML do Estoque inválido: {erro}"))
        return

    try:
        respostas = xml.parsear_xml_resposta_estoque(xml_bytes)
        ok = erro_count = 0

        for resp in respostas:
            codigo = resp["codigo_medicamento"]

            # Busca prescrições com esse código que ainda não têm retorno
            prescricoes = db.buscar_prescricoes_sem_retorno_por_codigo(codigo)

            if not prescricoes:
                erro_count += 1
                continue

            # Associa ao mais recente sem retorno
            for p in prescricoes:
                db.salvar_retorno_estoque(
                    id_prescricao=p["id"],
                    codigo_med=codigo,
                    disponivel=resp["disponivel"],
                    observacao=resp["observacao"],
                )
                ok += 1

        flash(("ok", f"Estoque importado: {ok} prescrição(ões) atualizada(s), {erro_count} sem correspondência."))

    except Exception as e:
        flash(("erro", f"Erro ao processar resposta do Estoque: {e}"))


def _importar_financeiro(xml_bytes):
    """
    Importa status_financeiro.xml do Financeiro.
    Valida contra financeiro_retorno.xsd deles e grava em status_financeiro.
    """
    valido, erro = xml.validar_xml(xml_bytes, config.XSD_FIN_RETORNO)
    if not valido:
        flash(("erro", f"XML do Financeiro inválido: {erro}"))
        return

    try:
        parsed   = xml.parsear_xml_financeiro(xml_bytes)
        data_ger = parsed["header"]["data_geracao"]
        hora_ger = parsed["header"]["hora_geracao"]
        ok = erro_count = 0

        for det in parsed["detalhes"]:
            if db.buscar_paciente(det["cpf_paciente"]):
                db.salvar_status_financeiro(
                    cpf=det["cpf_paciente"],
                    status_fin=det["status_financeiro"],
                    qtd_pendencias=det["qtd_pendencias"],
                    valor_pendente=det["valor_total_pendente"],
                    data_vencimento=det.get("data_vencimento"),
                    permite_atendimento=det["permite_atendimento"],
                    observacao=det.get("observacao"),
                    data_geracao_origem=data_ger,
                    hora_geracao_origem=hora_ger,
                )
                ok += 1
            else:
                erro_count += 1

        flash(("ok", f"Financeiro importado: {ok} paciente(s) atualizado(s), {erro_count} CPF(s) não encontrado(s)."))

    except Exception as e:
        flash(("erro", f"Erro ao processar arquivo do Financeiro: {e}"))
