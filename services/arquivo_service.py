# services/arquivo_service.py
# Responsável por toda a lógica de geração e salvamento de arquivos de integração.
# As rotas chamam estas funções — não fazem geração de arquivo diretamente.

import os
import hashlib
from datetime import datetime
from utils.formatters import pad_zero, pad_espaco, formatar_quantidade, formatar_valor_cents


def pasta_saida():
    """Retorna o caminho da pasta de saída, criando-a se não existir."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pasta = os.path.join(base, "arquivos", "saida")
    os.makedirs(pasta, exist_ok=True)
    return pasta


# -----------------------------------------------------------------------------
# PRESCRIÇÃO — gerado por evento (um arquivo por prescrição)
# -----------------------------------------------------------------------------
def gerar_prescricao(id_prescricao, atendimento, crm_medico,
                     codigo_medicamento, quantidade, unidade_medida,
                     observacao, data_prescricao, hora_prescricao):
    """
    Gera ATEND_PRESCRICAO_[AAMMDD]_[HHMMSS].txt — 200 bytes por linha.
    Chamado logo após o commit da prescrição no banco.
    """
    data_fmt = data_prescricao.strftime("%y%m%d")
    hora_fmt = hora_prescricao.strftime("%H%M%S")

    linha = (
        pad_zero(id_prescricao, 30) +           # 30 bytes
        pad_zero(atendimento["cpf_paciente"], 11) + # 11 bytes
        data_fmt +                               # 6 bytes
        hora_fmt +                               # 6 bytes
        pad_espaco(crm_medico, 15) +             # 15 bytes
        pad_zero(codigo_medicamento, 20) +       # 20 bytes
        formatar_quantidade(quantidade) +         # 8 bytes
        pad_espaco(unidade_medida, 4) +          # 4 bytes
        pad_espaco(observacao, 100)              # 100 bytes
    )                                            # Total: 200 bytes

    nome = f"ATEND_PRESCRICAO_{data_fmt}_{hora_fmt}.txt"
    caminho = os.path.join(pasta_saida(), nome)

    with open(caminho, "w", encoding="utf-8") as f:
        f.write(linha + "\n")

    return nome


# -----------------------------------------------------------------------------
# ENCERRAMENTO — arquivo diário acumulativo (H/D/T)
# -----------------------------------------------------------------------------
def gerar_encerramento(atendimento, cid_principal, procedimento,
                       qtd_medicamentos, valor_procedimentos, data_enc, hora_enc):
    """
    Gera ou atualiza ATEND_ENCERRAMENTO_[AAMMDD].txt.
    Múltiplos encerramentos do mesmo dia ficam no mesmo arquivo.
    O rodapé T é recalculado a cada novo encerramento.
    """
    data_fmt = data_enc.strftime("%y%m%d")
    hora_fmt = hora_enc.strftime("%H%M%S")

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

    nome    = f"ATEND_ENCERRAMENTO_{data_fmt}.txt"
    caminho = os.path.join(pasta_saida(), nome)

    # Abre em append se já existe, senão cria com cabeçalho
    modo = "a" if os.path.exists(caminho) else "w"
    header = "H" + data_fmt + hora_fmt + "01.00" + "000001"

    with open(caminho, modo, encoding="utf-8") as f:
        if modo == "w":
            f.write(header + "\n")
        f.write(registro_d + "\n")

    # Relê e reescreve para atualizar cabeçalho e rodapé com todos os registros do dia
    _recalcular_rodape(caminho, data_fmt, hora_fmt)

    return nome


def _recalcular_rodape(caminho, data_fmt, hora_fmt):
    """
    Relê o arquivo, remove rodapés antigos e reescreve com
    cabeçalho e rodapé atualizados para todos os registros D do dia.
    """
    with open(caminho, "r", encoding="utf-8") as f:
        linhas = [l.rstrip("\n") for l in f.readlines()]

    linhas       = [l for l in linhas if not l.startswith("T")]
    registros_d  = [l for l in linhas if l.startswith("D")]
    total        = str(len(registros_d)).zfill(6)

    # Soma os valores em centavos de todos os registros D (posição 85-97)
    soma_total = str(sum(
        int(l[85:97]) for l in registros_d if len(l) > 97
    )).zfill(16)

    conteudo_d = "".join(registros_d)
    novo_hash  = hashlib.md5(conteudo_d.encode("utf-8")).hexdigest().upper()

    # Atualiza o total de registros no cabeçalho
    if linhas and linhas[0].startswith("H"):
        linhas[0] = linhas[0][:17] + total

    linhas.append("T" + total + soma_total + novo_hash)

    with open(caminho, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")


# -----------------------------------------------------------------------------
# EXPORTAÇÃO MANUAL — lote por período
# -----------------------------------------------------------------------------
def exportar_prescricoes(registros, data_ini, data_fim):
    """Gera arquivo consolidado de prescrições para o período informado."""
    linhas = []
    for r in registros:
        data_fmt = r["data_prescricao"].strftime("%y%m%d")
        hora_fmt = r["hora_prescricao"].strftime("%H%M%S")
        linha = (
            pad_zero(r["id_prescricao"], 30) +
            pad_zero(r["cpf_paciente"], 11) +
            data_fmt + hora_fmt +
            pad_espaco(r["crm_medico"], 15) +
            pad_zero(r["codigo_medicamento"], 20) +
            formatar_quantidade(r["quantidade"]) +
            pad_espaco(r["unidade_medida"], 4) +
            pad_espaco(r["observacao"], 100)
        )
        linhas.append(linha)

    ini  = data_ini.replace("-","")[2:]
    fim  = data_fim.replace("-","")[2:]
    nome = f"ATEND_PRESCRICAO_{ini}_{fim}.txt"
    _salvar_simples(nome, linhas)
    return nome


def exportar_aberturas(registros, data_ini, data_fim):
    """Gera arquivo consolidado de aberturas de atendimento para o período."""
    linhas_d = []
    for r in registros:
        linha = (
            "D" +
            pad_zero(r["id_atendimento"], 30) +
            pad_zero(r["cpf_paciente"], 11) +
            r["data_abertura"].strftime("%y%m%d") +
            r["hora_abertura"].strftime("%H%M%S") +
            pad_espaco(r["tipo"], 1) +
            pad_espaco(r["crm_medico"], 15) +
            pad_espaco(r["especialidade"], 40) +
            pad_espaco(r["convenio"] or "PARTICULAR", 30) +
            pad_espaco(r["carteirinha"], 20) +
            pad_espaco(r["observacao"], 100)
        )
        linhas_d.append(linha)

    ini  = data_ini.replace("-","")[2:]
    fim  = data_fim.replace("-","")[2:]
    nome = f"ATEND_ABERTURA_{ini}_{fim}.txt"
    _salvar_hdt(nome, linhas_d)
    return nome


def exportar_encerramentos(registros, data_ini, data_fim):
    """Gera arquivo consolidado de encerramentos para o período."""
    linhas_d   = []
    soma_valor = 0

    for r in registros:
        valor      = float(r["valor_procedimentos"] or 0)
        soma_valor += valor
        linha = (
            "D" +
            pad_zero(r["id_atendimento"], 30) +
            pad_zero(r["cpf_paciente"], 11) +
            (r["data_encerramento"].strftime("%y%m%d") if r["data_encerramento"] else "000000") +
            (r["hora_encerramento"].strftime("%H%M%S") if r["hora_encerramento"] else "000000") +
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

    ini  = data_ini.replace("-","")[2:]
    fim  = data_fim.replace("-","")[2:]
    nome = f"ATEND_ENCERRAMENTO_{ini}_{fim}.txt"
    _salvar_hdt(nome, linhas_d, soma_valor=soma_valor)
    return nome


# -----------------------------------------------------------------------------
# Funções internas de salvamento
# -----------------------------------------------------------------------------
def _salvar_simples(nome, linhas):
    """Salva linhas diretamente, sem estrutura H/D/T."""
    caminho = os.path.join(pasta_saida(), nome)
    with open(caminho, "w", encoding="utf-8") as f:
        for l in linhas:
            f.write(l + "\n")


def _salvar_hdt(nome, linhas_d, soma_valor=0):
    """Salva arquivo com estrutura H (cabeçalho), D (detalhes) e T (rodapé com hash MD5)."""
    agora    = datetime.now()
    data_fmt = agora.strftime("%y%m%d")
    hora_fmt = agora.strftime("%H%M%S")
    total    = str(len(linhas_d)).zfill(6)

    conteudo_d = "".join(linhas_d)
    hash_md5   = hashlib.md5(conteudo_d.encode("utf-8")).hexdigest().upper()
    soma_fmt   = str(int(round(soma_valor * 100))).zfill(16)

    caminho = os.path.join(pasta_saida(), nome)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("H" + data_fmt + hora_fmt + "01.00" + total + "\n")
        for l in linhas_d:
            f.write(l + "\n")
        f.write("T" + total + soma_fmt + hash_md5 + "\n")
