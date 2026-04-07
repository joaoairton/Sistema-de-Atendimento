# services/db_service.py
# Operações no banco db_atendimento_xml.
#
# 6 tabelas, cada uma com papel de negócio claro:
#   paciente, atendimento, prescricao
#   status_financeiro  — dado do Financeiro, consultado na abertura
#   retorno_estoque    — dado do Estoque, consultado na tela de prescrição

from config import get_db, get_cur


# =============================================================================
# PACIENTE
# =============================================================================

def buscar_paciente(cpf):
    db = get_db(); cur = get_cur(db)
    try:
        cur.execute("SELECT * FROM paciente WHERE cpf = %s", (cpf,))
        return cur.fetchone()
    finally:
        cur.close(); db.close()

def cadastrar_paciente(cpf, nome, data_nasc=None, telefone=None, email=None):
    db = get_db(); cur = db.cursor()
    try:
        cur.execute("""
            INSERT INTO paciente (cpf, nome, data_nasc, telefone, email)
            VALUES (%s, %s, %s, %s, %s)
        """, (cpf, nome.upper(), data_nasc or None,
              telefone or None, email or None))
        db.commit()
    finally:
        cur.close(); db.close()

def listar_pacientes():
    db = get_db(); cur = get_cur(db)
    try:
        cur.execute("SELECT * FROM paciente ORDER BY nome")
        return cur.fetchall()
    finally:
        cur.close(); db.close()


# =============================================================================
# ATENDIMENTO
# =============================================================================

def abrir_atendimento(cpf, tipo, crm=None, convenio=None, carteirinha=None):
    db = get_db(); cur = db.cursor()
    try:
        cur.execute("""
            INSERT INTO atendimento
              (cpf_paciente, tipo, crm_medico, convenio, carteirinha)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (cpf, tipo, crm or None, convenio or None, carteirinha or None))
        id_atend = cur.fetchone()[0]
        db.commit()
        return id_atend
    finally:
        cur.close(); db.close()

def buscar_atendimento(id_atend):
    db = get_db(); cur = get_cur(db)
    try:
        cur.execute("""
            SELECT a.*, p.nome AS nome_paciente
            FROM atendimento a
            JOIN paciente p ON p.cpf = a.cpf_paciente
            WHERE a.id = %s
        """, (id_atend,))
        return cur.fetchone()
    finally:
        cur.close(); db.close()

def listar_atendimentos():
    db = get_db(); cur = get_cur(db)
    try:
        cur.execute("""
            SELECT a.id, a.tipo, a.status, a.data_abertura,
                   p.nome AS nome_paciente, a.cpf_paciente
            FROM atendimento a
            JOIN paciente p ON p.cpf = a.cpf_paciente
            ORDER BY a.data_abertura DESC, a.hora_abertura DESC
        """)
        return cur.fetchall()
    finally:
        cur.close(); db.close()

def finalizar_atendimento(id_atend, cid, codigo_tuss, valor_total, observacoes=None):
    db = get_db(); cur = db.cursor()
    try:
        cur.execute("""
            UPDATE atendimento SET
                status           = 'FINALIZADO',
                cid              = %s,
                codigo_tuss      = %s,
                valor_total      = %s,
                data_finalizacao = CURRENT_DATE,
                hora_finalizacao = CURRENT_TIME,
                observacoes      = %s
            WHERE id = %s AND status = 'ABERTO'
            RETURNING id, data_finalizacao, hora_finalizacao
        """, (cid, codigo_tuss, valor_total, observacoes or None, id_atend))
        row = cur.fetchone()
        db.commit()
        return row
    finally:
        cur.close(); db.close()


# =============================================================================
# PRESCRIÇÃO
# =============================================================================

def registrar_prescricao(id_atend, cpf, crm, codigo_med,
                          quantidade, unidade, instrucoes=None):
    db = get_db(); cur = db.cursor()
    try:
        unidade_fmt = unidade.strip().upper().ljust(4)[:4]
        cur.execute("""
            INSERT INTO prescricao
              (id_atendimento, cpf_paciente, crm_medico,
               codigo_med, quantidade, unidade, instrucoes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, data_prescricao, hora_prescricao
        """, (id_atend, cpf, crm or None,
              codigo_med, quantidade, unidade_fmt, instrucoes or None))
        row = cur.fetchone()
        db.commit()
        return row[0], row[1], row[2]
    finally:
        cur.close(); db.close()

def buscar_prescricao(id_pres):
    db = get_db(); cur = get_cur(db)
    try:
        cur.execute("SELECT * FROM prescricao WHERE id = %s", (id_pres,))
        return cur.fetchone()
    finally:
        cur.close(); db.close()

def buscar_prescricoes_atendimento(id_atend):
    """
    Retorna prescrições com retorno do estoque (LEFT JOIN).
    disponivel e obs_estoque vêm nulos se o estoque ainda não respondeu.
    reserva_confirmada indica se o XML de reserva já foi gerado.
    """
    db = get_db(); cur = get_cur(db)
    try:
        cur.execute("""
            SELECT p.*,
                   re.disponivel          AS disponivel,
                   re.observacao          AS obs_estoque,
                   re.reserva_confirmada  AS reserva_confirmada,
                   re.id                  AS id_retorno
            FROM prescricao p
            LEFT JOIN retorno_estoque re ON re.id_prescricao = p.id
            WHERE p.id_atendimento = %s
            ORDER BY p.data_prescricao, p.hora_prescricao
        """, (id_atend,))
        return cur.fetchall()
    finally:
        cur.close(); db.close()


# =============================================================================
# STATUS FINANCEIRO
# Populado pela importação do Financeiro.
# O sistema consulta sempre o registro mais recente por CPF.
# =============================================================================

def salvar_status_financeiro(cpf, status_fin, qtd_pendencias,
                              valor_pendente, data_vencimento,
                              permite_atendimento, observacao,
                              data_geracao_origem, hora_geracao_origem):
    db = get_db(); cur = db.cursor()
    try:
        cur.execute("""
            INSERT INTO status_financeiro
              (cpf_paciente, status_financeiro, qtd_pendencias,
               valor_total_pendente, data_vencimento,
               permite_atendimento, observacao,
               data_geracao_origem, hora_geracao_origem)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (cpf, status_fin, qtd_pendencias, valor_pendente,
              data_vencimento, permite_atendimento, observacao,
              data_geracao_origem, hora_geracao_origem))
        db.commit()
    finally:
        cur.close(); db.close()

def buscar_status_financeiro(cpf):
    """Retorna o registro mais recente — é o que o sistema usa para decisão."""
    db = get_db(); cur = get_cur(db)
    try:
        cur.execute("""
            SELECT * FROM status_financeiro
            WHERE cpf_paciente = %s
            ORDER BY importado_em DESC
            LIMIT 1
        """, (cpf,))
        return cur.fetchone()
    finally:
        cur.close(); db.close()


# =============================================================================
# RETORNO ESTOQUE
# Populado pela importação do Estoque.
# Consultado via JOIN em buscar_prescricoes_atendimento.
# =============================================================================

def salvar_retorno_estoque(id_prescricao, codigo_med, disponivel, observacao):
    """Grava retorno do Estoque. reserva_confirmada=False até gerar a reserva."""
    db = get_db(); cur = db.cursor()
    try:
        cur.execute("""
            INSERT INTO retorno_estoque
              (id_prescricao, codigo_med, disponivel,
               observacao, reserva_confirmada)
            VALUES (%s, %s, %s, %s, FALSE)
        """, (id_prescricao, codigo_med, disponivel, observacao or None))
        db.commit()
    finally:
        cur.close(); db.close()


def buscar_prescricoes_sem_retorno_por_codigo(codigo_med):
    """
    Busca prescrições com o código de medicamento informado que ainda
    não têm retorno do Estoque (LEFT JOIN com retorno_estoque IS NULL).
    Usada para associar a resposta do Estoque — que não inclui id_prescricao
    no schema resposta.xsd.
    """
    db = get_db(); cur = get_cur(db)
    try:
        cur.execute("""
            SELECT p.*
            FROM prescricao p
            LEFT JOIN retorno_estoque re ON re.id_prescricao = p.id
            WHERE p.codigo_med = %s
              AND re.id IS NULL
            ORDER BY p.data_prescricao DESC, p.hora_prescricao DESC
        """, (codigo_med,))
        return cur.fetchall()
    finally:
        cur.close(); db.close()


def confirmar_reserva(id_prescricao: int):
    """
    Marca a reserva como confirmada após gerar o XML de reserva.
    Chamada pela rota após gerar e salvar o XML de reserva com sucesso.
    """
    db = get_db(); cur = db.cursor()
    try:
        cur.execute("""
            UPDATE retorno_estoque
            SET reserva_confirmada = TRUE
            WHERE id_prescricao = %s
        """, (id_prescricao,))
        db.commit()
    finally:
        cur.close(); db.close()


def prescricoes_pendentes_reserva(id_atend: int):
    """
    Retorna prescrições que bloqueiam a finalização. Dois casos:
    1. Sem resposta do Estoque ainda (nenhuma linha em retorno_estoque)
    2. Disponível mas reserva ainda não confirmada
    """
    db = get_db(); cur = get_cur(db)
    try:
        cur.execute("""
            SELECT p.id, p.codigo_med, p.quantidade,
                   re.disponivel,
                   re.reserva_confirmada
            FROM prescricao p
            LEFT JOIN retorno_estoque re ON re.id_prescricao = p.id
            WHERE p.id_atendimento = %s
              AND (
                  re.id IS NULL                                    -- sem resposta do Estoque
                  OR (re.disponivel = TRUE                         -- disponível mas
                      AND re.reserva_confirmada = FALSE)           -- reserva não confirmada
              )
        """, (id_atend,))
        return cur.fetchall()
    finally:
        cur.close(); db.close()
