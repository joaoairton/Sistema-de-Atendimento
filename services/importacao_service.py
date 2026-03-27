# services/importacao_service.py
# Lógica de importação dos arquivos recebidos dos sistemas externos.
# Valida estrutura, hash MD5 e grava os dados no banco.

import hashlib
from datetime import date, time


def _validar_hdt(linhas, nome_arquivo):
    """
    Valida a estrutura H/D/T de um arquivo.
    Levanta ValueError se qualquer verificação falhar.
    Retorna a lista de registros D válidos.
    """
    if not linhas:
        raise ValueError(f"Arquivo vazio.")

    # Cabeçalho
    if not linhas[0].startswith("H"):
        raise ValueError("Arquivo inválido: primeira linha não é um cabeçalho H.")

    header         = linhas[0]
    total_esperado = int(header[17:23])

    # Rodapé
    if not linhas[-1].startswith("T"):
        raise ValueError("Arquivo inválido: última linha não é um rodapé T.")

    # Registros D
    registros_d = [l for l in linhas if l.startswith("D")]

    if len(registros_d) != total_esperado:
        raise ValueError(
            f"Arquivo rejeitado: cabeçalho indica {total_esperado} registro(s), "
            f"mas foram encontrados {len(registros_d)}."
        )

    # Hash MD5
    trailer      = linhas[-1]
    hash_arquivo = trailer[37:69]  # T(1)+TOTAL(6)+SOMA(18)+QTD_BLOQ(6)+QTD_REG(6) = pos 37
    conteudo_d   = "".join(registros_d)
    hash_calculado = hashlib.md5(conteudo_d.encode("utf-8")).hexdigest().upper()

    if hash_calculado != hash_arquivo:
        raise ValueError(
            "Arquivo rejeitado: hash MD5 inválido. "
            "O arquivo pode ter sido corrompido ou alterado."
        )

    return registros_d


# -----------------------------------------------------------------------------
# IMPORTAR RETORNO DO ESTOQUE
# Formato esperado (por linha, sem H/D/T — arquivo simples):
#   id_prescricao(30) + codigo_medicamento(20) + disponivel(1) + observacao(100)
#   Total: 151 bytes
# -----------------------------------------------------------------------------
def importar_retorno_estoque(conteudo, cur):
    """
    Lê o arquivo de retorno do Estoque e grava na tabela retorno_estoque.
    Atualiza o campo disponivel de cada prescrição correspondente.
    """
    linhas = [l.rstrip("\n") for l in conteudo.splitlines() if l.strip()]

    if not linhas:
        raise ValueError("Arquivo vazio.")

    processados = 0
    erros       = []

    for i, linha in enumerate(linhas, 1):
        if len(linha) < 51:
            erros.append(f"Linha {i}: tamanho inválido ({len(linha)} bytes).")
            continue

        try:
            id_prescricao      = int(linha[0:30].strip())
            codigo_medicamento = int(linha[30:50].strip())
            disponivel         = int(linha[50:51].strip())
            observacao         = linha[51:151].strip() if len(linha) > 51 else ""

            # Verifica se a prescrição existe
            cur.execute("SELECT id_prescricao FROM prescricao WHERE id_prescricao = %s",
                        (id_prescricao,))
            if not cur.fetchone():
                erros.append(f"Linha {i}: prescrição #{id_prescricao} não encontrada.")
                continue

            # Grava o retorno na tabela retorno_estoque
            cur.execute("""
                INSERT INTO retorno_estoque
                    (id_prescricao, codigo_medicamento, disponivel, observacao)
                VALUES (%s, %s, %s, %s)
            """, (id_prescricao, codigo_medicamento, disponivel,
                  observacao or None))

            # Atualiza o status_estoque na tabela prescricao para exibição na tela
            status = 'DISPONIVEL' if disponivel == 1 else 'INDISPONIVEL'
            cur.execute("""
                UPDATE prescricao SET status_estoque = %s
                WHERE id_prescricao = %s
            """, (status, id_prescricao))

            processados += 1

        except (ValueError, IndexError) as e:
            erros.append(f"Linha {i}: erro ao processar — {str(e)}")

    if processados == 0 and erros:
        raise ValueError(
            f"Nenhum registro processado. Erros encontrados:\n" + "\n".join(erros))

    return {"processados": processados, "erros": erros}


# -----------------------------------------------------------------------------
# IMPORTAR STATUS FINANCEIRO
# Formato esperado: arquivo com estrutura H/D/T
# Registro D: TIPO(1) + CPF(11) + STATUS(1) + QTD_PEND(3) +
#             VALOR(14) + DATA_VENC(6) + PERMITE(1) + OBS(100)
#             Total D: 137 bytes
# -----------------------------------------------------------------------------
def importar_status_financeiro(conteudo, cur):
    """
    Lê o arquivo de status financeiro do Financeiro e grava na tabela status_financeiro.
    Usa estrutura H/D/T com validação de hash MD5.
    """
    linhas = [l.rstrip("\n") for l in conteudo.splitlines() if l.strip()]

    # Valida estrutura H/D/T e hash
    registros_d = _validar_hdt(linhas, "status_financeiro")

    # Extrai data de geração do cabeçalho
    header       = linhas[0]
    data_ger_str = header[1:7]    # AAMMDD
    hora_ger_str = header[7:13]   # HHMMSS

    try:
        data_geracao = date(
            2000 + int(data_ger_str[0:2]),
            int(data_ger_str[2:4]),
            int(data_ger_str[4:6])
        )
        hora_geracao = time(
            int(hora_ger_str[0:2]),
            int(hora_ger_str[2:4]),
            int(hora_ger_str[4:6])
        )
    except ValueError:
        raise ValueError("Data ou hora de geração inválida no cabeçalho.")

    processados = 0
    erros       = []

    for i, linha in enumerate(registros_d, 1):
        if len(linha) < 32:
            erros.append(f"Registro D {i}: tamanho inválido.")
            continue

        try:
            # Lê cada campo na posição exata conforme o layout do Financeiro
            cpf_paciente    = linha[1:12].strip()
            status_fin      = linha[12:13].strip()
            qtd_pendencias  = int(linha[13:16].strip() or "0")
            valor_pendente  = int(linha[16:30].strip() or "0") / 100  # centavos → reais
            data_venc_str   = linha[30:36].strip()
            permite         = linha[36:37].strip()
            observacao      = linha[37:137].strip() if len(linha) > 37 else ""

            # Converte data de vencimento (pode vir vazia)
            data_venc = None
            if data_venc_str and data_venc_str != "000000":
                try:
                    data_venc = date(
                        2000 + int(data_venc_str[0:2]),
                        int(data_venc_str[2:4]),
                        int(data_venc_str[4:6])
                    )
                except ValueError:
                    pass

            # Verifica se o paciente existe no sistema
            cur.execute("SELECT cpf FROM paciente WHERE cpf = %s", (cpf_paciente,))
            if not cur.fetchone():
                erros.append(f"Registro {i}: CPF {cpf_paciente} não encontrado no sistema.")
                continue

            # Grava o status financeiro
            cur.execute("""
                INSERT INTO status_financeiro
                    (cpf_paciente, status_financeiro, qtd_pendencias,
                     valor_total_pendente, data_vencimento_mais_antiga,
                     permite_atendimento, observacao,
                     data_geracao, hora_geracao)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (cpf_paciente, status_fin, qtd_pendencias,
                  valor_pendente, data_venc, permite,
                  observacao or None, data_geracao, hora_geracao))

            processados += 1

        except Exception as e:
            erros.append(f"Registro {i}: erro — {str(e)}")

    if processados == 0 and erros:
        raise ValueError(
            "Nenhum registro processado. Erros:\n" + "\n".join(erros))

    return {"processados": processados, "erros": erros}
