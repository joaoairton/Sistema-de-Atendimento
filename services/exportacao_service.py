"""
services/exportacao_service.py — Logica de exportacao manual de arquivos.

Contem as funcoes que montam e salvam os tres tipos de arquivo:
prescricao, abertura e encerramento — tanto para geracao automatica
quanto para exportacao manual por periodo.
"""

import os
import hashlib
from datetime import datetime
from utils.formatters import (
    pad_zero, pad_espaco, formatar_data, formatar_hora,
    formatar_quantidade, formatar_valor_cents, calcular_hash
)


# ---------------------------------------------------------------------------
# Exportacao por periodo (chamada pela rota de exportacao manual)
# ---------------------------------------------------------------------------

def exportar_prescricoes(registros, data_ini, data_fim):
    """Gera arquivo consolidado de prescricoes de um periodo."""
    linhas = []
    for r in registros:
        linha = (
            pad_zero(r["id_prescricao"], 30) +
            pad_zero(r["cpf_paciente"], 11) +
            formatar_data(r["data_prescricao"]) +
            formatar_hora(r["hora_prescricao"]) +
            pad_espaco(r["crm_medico"], 15) +
            pad_zero(r["codigo_medicamento"], 20) +
            formatar_quantidade(r["quantidade"]) +
            pad_espaco(r["unidade_medida"], 4) +
            pad_espaco(r["observacao"], 100)
        )
        linhas.append(linha)

    ini, fim = _periodo(data_ini, data_fim)
    nome = f"ATEND_PRESCRICAO_{ini}_{fim}.txt"
    salvar_arquivo(nome, linhas, tipo="simples")
    return nome


def exportar_aberturas(registros, data_ini, data_fim):
    """Gera arquivo consolidado de aberturas de atendimento de um periodo."""
    linhas_d = []
    for r in registros:
        linha = (
            "D" +
            pad_zero(r["id_atendimento"], 30) +
            pad_zero(r["cpf_paciente"], 11) +
            formatar_data(r["data_abertura"]) +
            formatar_hora(r["hora_abertura"]) +
            pad_espaco(r["tipo"], 1) +
            pad_espaco(r["crm_medico"], 15) +
            pad_espaco(r["especialidade"], 40) +
            pad_espaco(r["convenio"] or "PARTICULAR", 30) +
            pad_espaco(r["carteirinha"], 20) +
            pad_espaco(r["observacao"], 100)
        )
        linhas_d.append(linha)

    ini, fim = _periodo(data_ini, data_fim)
    nome = f"ATEND_ABERTURA_{ini}_{fim}.txt"
    salvar_arquivo(nome, linhas_d, tipo="hdt")
    return nome


def exportar_encerramentos(registros, data_ini, data_fim):
    """Gera arquivo consolidado de encerramentos de atendimento de um periodo."""
    linhas_d  = []
    soma_valor = 0

    for r in registros:
        valor = float(r["valor_procedimentos"] or 0)
        soma_valor += valor
        linha = (
            "D" +
            pad_zero(r["id_atendimento"], 30) +
            pad_zero(r["cpf_paciente"], 11) +
            (formatar_data(r["data_encerramento"]) if r["data_encerramento"] else "000000") +
            (formatar_hora(r["hora_encerramento"]) if r["hora_encerramento"] else "000000") +
            pad_espaco(r["tipo"], 1) +
            pad_espaco(r["crm_medico"], 15) +
            pad_espaco(r["cid_principal"], 10) +
            pad_espaco(r["procedimento"], 20) +
            pad_zero(r["qtd_medicamentos"] or 0, 3) +
            formatar_valor_cents(valor) +
            pad_espaco(r["convenio"] or "PARTICULAR", 30) +
            pad_espaco(r["carteirinha"], 20) +
            pad_espaco(r["observacao"], 100)
        )
        linhas_d.append(linha)

    ini, fim = _periodo(data_ini, data_fim)
    nome = f"ATEND_ENCERRAMENTO_{ini}_{fim}.txt"
    salvar_arquivo(nome, linhas_d, tipo="hdt", soma_valor=soma_valor)
    return nome


# ---------------------------------------------------------------------------
# Geracao por evento (chamada ao encerrar atendimento)
# ---------------------------------------------------------------------------

def gerar_arquivo_encerramento(atendimento, prescricoes, cid_principal,
                                procedimento, qtd_medicamentos,
                                valor_procedimentos, data_enc, hora_enc):
    """
    Gera ou atualiza o arquivo diario ATEND_ENCERRAMENTO_[AAMMDD].txt.

    Multiplos encerramentos do mesmo dia ficam no mesmo arquivo.
    O sistema reescreve o arquivo inteiro a cada encerramento para manter
    o cabecalho H e rodape T consistentes com o total e hash corretos.
    """
    data_fmt = formatar_data(data_enc)
    hora_fmt = formatar_hora(hora_enc)

    registro_d = (
        "D" +
        pad_zero(atendimento["id_atendimento"], 30) +
        pad_zero(atendimento["cpf_paciente"], 11) +
        data_fmt + hora_fmt +
        pad_espaco(atendimento["tipo"], 1) +
        pad_espaco(atendimento["crm_medico"], 15) +
        pad_espaco(cid_principal, 10) +
        pad_espaco(procedimento, 20) +
        pad_zero(qtd_medicamentos, 3) +
        formatar_valor_cents(valor_procedimentos) +
        pad_espaco(atendimento["convenio"] or "PARTICULAR", 30) +
        pad_espaco(atendimento["carteirinha"], 20) +
        pad_espaco(atendimento["observacao"], 100)
    )

    pasta  = _pasta_saida()
    nome_arquivo = f"ATEND_ENCERRAMENTO_{data_fmt}.txt"
    caminho = os.path.join(pasta, nome_arquivo)

    # Append se o arquivo do dia ja existe, senao cria com cabecalho
    modo = "a" if os.path.exists(caminho) else "w"
    with open(caminho, modo, encoding="utf-8") as f:
        if modo == "w":
            header = "H" + data_fmt + hora_fmt + "01.00" + "000001"
            f.write(header + "\n")
        f.write(registro_d + "\n")

    # Rele e reescreve o arquivo completo para atualizar cabecalho e rodape
    with open(caminho, "r", encoding="utf-8") as f:
        linhas = [l.rstrip("\n") for l in f.readlines()]

    linhas       = [l for l in linhas if not l.startswith("T")]
    registros_d  = [l for l in linhas if l.startswith("D")]
    total        = pad_zero(len(registros_d), 6)
    soma_total   = pad_zero(sum(int(l[85:97]) for l in registros_d if len(l) > 97), 16)
    novo_hash    = calcular_hash(registros_d)
    novo_trailer = "T" + total + soma_total + novo_hash

    if linhas and linhas[0].startswith("H"):
        linhas[0] = linhas[0][:17] + total

    linhas.append(novo_trailer)

    with open(caminho, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")

    return nome_arquivo


# ---------------------------------------------------------------------------
# Funcao base de escrita de arquivo
# ---------------------------------------------------------------------------

def salvar_arquivo(nome, linhas, tipo="simples", soma_valor=0):
    """
    Salva as linhas em um arquivo na pasta arquivos/saida/.

    tipo='simples' -> grava as linhas diretamente, sem H/D/T.
    tipo='hdt'     -> envolve com cabecalho H e rodape T com hash MD5.
    """
    pasta   = _pasta_saida()
    caminho = os.path.join(pasta, nome)
    agora   = datetime.now()

    with open(caminho, "w", encoding="utf-8") as f:
        if tipo == "hdt":
            total    = pad_zero(len(linhas), 6)
            data_fmt = agora.strftime("%y%m%d")
            hora_fmt = agora.strftime("%H%M%S")
            header   = "H" + data_fmt + hora_fmt + "01.00" + total
            f.write(header + "\n")
            for l in linhas:
                f.write(l + "\n")
            hash_md5  = calcular_hash(linhas)
            soma_fmt  = pad_zero(int(round(soma_valor * 100)), 16)
            trailer   = "T" + total + soma_fmt + hash_md5
            f.write(trailer + "\n")
        else:
            for l in linhas:
                f.write(l + "\n")


# ---------------------------------------------------------------------------
# Auxiliar interno
# ---------------------------------------------------------------------------

def _pasta_saida():
    raiz  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pasta = os.path.join(raiz, "arquivos", "saida")
    os.makedirs(pasta, exist_ok=True)
    return pasta

def _periodo(data_ini, data_fim):
    ini = data_ini.replace("-", "")[2:]
    fim = data_fim.replace("-", "")[2:]
    return ini, fim
