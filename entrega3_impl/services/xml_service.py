# services/xml_service.py
# Geração e validação de XMLs de integração — Entrega 3.
# Usa lxml. Independente da lógica de largura fixa da Entrega 2.
#
# INTEGRAÇÕES:
#   SAÍDA  → Estoque:    gerar_xml_consulta()   (consulta.xsd do Estoque)
#   SAÍDA  → Financeiro: gerar_xml_finalizacao() (finalizacao.xsd nosso)
#   ENTRADA← Estoque:    parsear_xml_resposta()  (resposta.xsd do Estoque)
#   ENTRADA← Financeiro: parsear_xml_financeiro() (financeiro_retorno.xsd deles)

import os
from datetime import datetime
from lxml import etree
import config

NS_PRESCRICAO  = "http://uniavan.edu.br/interop/prescricao"
NS_FINALIZACAO = "http://uniavan.edu.br/interop/finalizacao"


# =============================================================================
# VALIDAÇÃO
# =============================================================================

def validar_xml(xml_bytes: bytes, caminho_xsd: str) -> tuple:
    """
    Valida xml_bytes contra o XSD em caminho_xsd.
    Retorna (True, '') ou (False, 'mensagem de erro').
    """
    try:
        schema = etree.XMLSchema(etree.parse(caminho_xsd))
        schema.assertValid(etree.fromstring(xml_bytes))
        return True, ""
    except etree.DocumentInvalid as e:
        return False, str(e)
    except Exception as e:
        return False, f"Erro de parse: {e}"


# =============================================================================
# SAÍDA → ESTOQUE: XML de consulta de disponibilidade
# Segue exatamente o consulta.xsd do Estoque.
# Pode conter uma ou mais prescrições no mesmo arquivo.
# =============================================================================

def gerar_xml_consulta_estoque(prescricoes: list) -> bytes:
    """
    Gera XML de consulta de disponibilidade no formato do Estoque.
    prescricoes: lista de dicts da tabela prescricao.

    Estrutura (consulta.xsd):
      <consultas>
        <consulta>
          <prescricao>42</prescricao>
          <cpf>04532198760</cpf>
          <codigo_medicamento>453</codigo_medicamento>
          <quantidade>1.5</quantidade>
        </consulta>
        ...
      </consultas>

    Sem namespace — o Estoque não usa namespace no schema.
    """
    raiz = etree.Element("consultas")

    for p in prescricoes:
        c = etree.SubElement(raiz, "consulta")
        _el_s(c, "prescricao",         str(p["id"]))
        _el_s(c, "cpf",                str(p["cpf_paciente"]))
        _el_s(c, "codigo_medicamento", str(p["codigo_med"]))
        _el_s(c, "quantidade",         str(p["quantidade"]))

    return etree.tostring(raiz, pretty_print=True,
                          xml_declaration=True, encoding="UTF-8")


def gerar_xml_reserva_estoque(prescricoes: list) -> bytes:
    """
    Gera XML de reserva de medicamento no formato do Estoque.
    Estrutura idêntica à consulta, mas com elemento raiz <reservas>/<reserva>.
    """
    raiz = etree.Element("reservas")

    for p in prescricoes:
        r = etree.SubElement(raiz, "reserva")
        _el_s(r, "prescricao",         str(p["id"]))
        _el_s(r, "cpf",                str(p["cpf_paciente"]))
        _el_s(r, "codigo_medicamento", str(p["codigo_med"]))
        _el_s(r, "quantidade",         str(p["quantidade"]))

    return etree.tostring(raiz, pretty_print=True,
                          xml_declaration=True, encoding="UTF-8")


# =============================================================================
# SAÍDA → FINANCEIRO: XML de finalização de atendimento
# Segue finalizacao.xsd (nosso schema).
# =============================================================================

def gerar_xml_finalizacao(atendimento: dict, prescricoes: list) -> bytes:
    """
    Gera XML de finalização conforme finalizacao.xsd.
    Contém apenas o essencial para o Financeiro realizar o faturamento.
    """
    raiz = etree.Element("finalizacaoAtendimento")

    _el_s(raiz, "id_atendimento",   str(atendimento["id"]))
    _el_s(raiz, "cpf_paciente",     atendimento["cpf_paciente"])
    _el_s(raiz, "data_atendimento", str(atendimento["data_finalizacao"]))
    _el_s(raiz, "tipo_atendimento", atendimento["tipo"])
    _el_s(raiz, "cid",              atendimento["cid"] or "")
    _el_s(raiz, "codigo_tuss",      atendimento["codigo_tuss"] or "")
    _el_s(raiz, "convenio",         atendimento["convenio"] or "PARTICULAR")

    if atendimento.get("carteirinha"):
        _el_s(raiz, "carteirinha", atendimento["carteirinha"])

    _el_s(raiz, "qtd_medicamentos", str(len(prescricoes)))
    _el_s(raiz, "valor_total",
          str(atendimento["valor_total"] or "0.00"))

    if atendimento.get("observacoes"):
        _el_s(raiz, "observacoes", atendimento["observacoes"])

    return etree.tostring(raiz, pretty_print=True,
                          xml_declaration=True, encoding="UTF-8")


# =============================================================================
# ENTRADA ← ESTOQUE: parseia resposta.xml recebido do Estoque
# Segue resposta.xsd do Estoque.
#
# LIMITAÇÃO CONHECIDA DO SCHEMA DO ESTOQUE:
# O resposta.xsd não inclui o campo <prescricao> — só tem codigo_medicamento.
# O sistema associa pelo codigo_medicamento nas prescrições abertas do paciente.
# =============================================================================

def parsear_xml_resposta_estoque(xml_bytes: bytes) -> list:
    """
    Lê XML de resposta do Estoque.
    Retorna lista de dicts: [{codigo_medicamento, disponivel, observacao}]

    Nota: sem id_prescricao no schema do Estoque — a associação é feita
    em routes/integracao.py pelo codigo_medicamento.
    """
    doc   = etree.fromstring(xml_bytes)
    itens = []

    for resp in doc.findall("resposta"):
        itens.append({
            "codigo_medicamento": int(resp.findtext("codigo_medicamento")),
            "disponivel":         int(resp.findtext("disponivel")) == 1,
            "observacao":         resp.findtext("observacao") or "",
        })

    return itens


# =============================================================================
# ENTRADA ← FINANCEIRO: parseia status_financeiro.xml
# Segue financeiro_retorno.xsd da equipe do Financeiro.
# Datas em AAMMDD, hash MD5 em minúsculas.
# =============================================================================

def parsear_xml_financeiro(xml_bytes: bytes) -> dict:
    """
    Lê XML de status_financeiro recebido do Financeiro.
    Retorna dict com header, lista de detalhes e trailer.
    Valida total do trailer antes de retornar.
    """
    doc = etree.fromstring(xml_bytes)

    header = doc.find("header")
    resultado = {
        "header": {
            "data_geracao":  _aammdd_para_date(header.findtext("data_geracao")),
            "hora_geracao":  _hhmmss_para_time(header.findtext("hora_geracao")),
            "versao_layout": header.findtext("versao_layout"),
        },
        "detalhes": [],
        "trailer":  {}
    }

    for det in doc.findall(".//detalhe"):
        venc = det.findtext("data_vencimento_mais_antiga") or ""
        resultado["detalhes"].append({
            "cpf_paciente":         det.findtext("cpf_paciente"),
            "status_financeiro":    det.findtext("status_financeiro"),
            "qtd_pendencias":       int(det.findtext("qtd_pendencias") or 0),
            "valor_total_pendente": float(det.findtext("valor_total_pendente") or 0),
            "data_vencimento":      _aammdd_para_date(venc) if venc else None,
            "permite_atendimento":  det.findtext("permite_atendimento"),
            "observacao":           det.findtext("observacao") or "",
        })

    trailer = doc.find("trailer")
    resultado["trailer"] = {
        "total_detalhes":   int(trailer.findtext("total_detalhes") or 0),
        "soma_valor_total": float(trailer.findtext("soma_valor_total") or 0),
        "qtd_bloqueados":   int(trailer.findtext("qtd_bloqueados") or 0),
        "qtd_regulares":    int(trailer.findtext("qtd_regulares") or 0),
        "hash_controle":    trailer.findtext("hash_controle"),
    }

    n_lidos = len(resultado["detalhes"])
    n_decl  = resultado["trailer"]["total_detalhes"]
    if n_lidos != n_decl:
        raise ValueError(
            f"Trailer declara {n_decl} registros, encontrados {n_lidos}."
        )

    return resultado


# =============================================================================
# SALVAR EM DISCO
# =============================================================================

def salvar_xml(conteudo: bytes, nome: str, pasta: str) -> str:
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, nome)
    with open(caminho, "wb") as f:
        f.write(conteudo)
    return caminho


def nome_consulta(id_atend: int) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"CONSULTA_ESTOQUE_{id_atend}_{ts}.xml"

def nome_reserva(id_atend: int) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"RESERVA_ESTOQUE_{id_atend}_{ts}.xml"

def nome_finalizacao(id_atend: int) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"FINALIZACAO_{id_atend}_{ts}.xml"


# =============================================================================
# AUXILIARES INTERNAS
# =============================================================================

def _sub(pai, ns, tag):
    """Cria subelemento com namespace."""
    return etree.SubElement(pai, f"{{{ns}}}{tag}")

def _el(pai, ns, tag, texto):
    """Cria subelemento com namespace e texto."""
    el = etree.SubElement(pai, f"{{{ns}}}{tag}")
    el.text = texto
    return el

def _el_s(pai, tag, texto):
    """Cria subelemento SEM namespace (para XMLs do Estoque)."""
    el = etree.SubElement(pai, tag)
    el.text = texto
    return el

def _aammdd_para_date(s: str):
    from datetime import date
    if not s or len(s) != 6:
        return None
    try:
        return date(2000 + int(s[0:2]), int(s[2:4]), int(s[4:6]))
    except ValueError:
        return None

def _hhmmss_para_time(s: str):
    from datetime import time
    if not s or len(s) != 6:
        return None
    try:
        return time(int(s[0:2]), int(s[2:4]), int(s[4:6]))
    except ValueError:
        return None
