"""
services/prescricao_service.py — Logica de geracao do arquivo de prescricao.

Separa a regra de negocio (montar e salvar o arquivo)
da rota HTTP (receber o formulario e responder ao navegador).
"""

import os
from utils.formatters import (
    pad_zero, pad_espaco, formatar_data, formatar_hora, formatar_quantidade
)


def gerar_arquivo_prescricao(id_prescricao, atendimento, crm_medico,
                              codigo_medicamento, quantidade, unidade_medida,
                              observacao, data_prescricao, hora_prescricao):
    """
    Gera o arquivo ATEND_PRESCRICAO no formato de largura fixa (200 bytes).

    Layout dos campos:
      id_prescricao      -> 30 bytes  (NUM, zeros a esquerda)
      cpf_paciente       -> 11 bytes  (NUM, zeros a esquerda)
      data_prescricao    -> 6 bytes   (AAMMDD)
      hora_prescricao    -> 6 bytes   (HHMMSS)
      crm_medico         -> 15 bytes  (CHAR, espacos a direita)
      codigo_medicamento -> 20 bytes  (NUM, zeros a esquerda)
      quantidade         -> 8 bytes   (sem separador: 1.5 -> 00001500)
      unidade_medida     -> 4 bytes   (CHAR, espacos a direita)
      observacao         -> 100 bytes (CHAR, espacos a direita)
    """
    linha = (
        pad_zero(id_prescricao, 30) +
        pad_zero(atendimento["cpf_paciente"], 11) +
        formatar_data(data_prescricao) +
        formatar_hora(hora_prescricao) +
        pad_espaco(crm_medico, 15) +
        pad_zero(codigo_medicamento, 20) +
        formatar_quantidade(quantidade) +
        pad_espaco(unidade_medida, 4) +
        pad_espaco(observacao, 100)
    )

    pasta_saida = _pasta_saida()
    nome_arquivo = f"ATEND_PRESCRICAO_{formatar_data(data_prescricao)}_{formatar_hora(hora_prescricao)}.txt"
    caminho = os.path.join(pasta_saida, nome_arquivo)

    with open(caminho, "w", encoding="utf-8") as f:
        f.write(linha + "\n")

    return nome_arquivo


def _pasta_saida():
    """Garante que a pasta arquivos/saida existe e retorna o caminho."""
    # __file__ aponta para services/prescricao_service.py
    # dois niveis acima chega na raiz do projeto
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pasta = os.path.join(raiz, "arquivos", "saida")
    os.makedirs(pasta, exist_ok=True)
    return pasta
