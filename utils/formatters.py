# utils/formatters.py
# Funções utilitárias de formatação de campos.
# Usadas tanto nas rotas quanto nos serviços de exportação.

def pad_zero(valor, tamanho):
    """Preenche com zeros à esquerda até atingir o tamanho. Ex: 453 → "00000000000000000453" """
    return str(valor or "").zfill(tamanho)

def pad_espaco(valor, tamanho):
    """Trunca e preenche com espaços à direita até atingir o tamanho."""
    return str(valor or "")[:tamanho].ljust(tamanho)

def formatar_quantidade(quantidade):
    """
    Converte quantidade decimal para inteiro sem separador (8 bytes).
    Ex: 1.5 → multiplica por 1000 → 1500 → zfill(8) → "00001500"
    """
    qtd_num = float(str(quantidade).replace(",", "."))
    return str(int(round(qtd_num * 1000))).zfill(8)

def formatar_valor_cents(valor):
    """
    Converte valor monetário para centavos sem separador (12 bytes).
    Ex: 180.00 → 18000 → "000000018000"
    """
    return str(int(round(float(valor or 0) * 100))).zfill(12)

def limpar_cpf(valor):
    """Remove pontuação do CPF. Ex: 045.321.987-60 → 04532198760"""
    return str(valor or "").replace(".", "").replace("-", "")

def limpar_telefone(valor):
    """Remove pontuação do telefone. Ex: (47) 9999-9999 → 4799999999"""
    return str(valor or "").replace("(","").replace(")","").replace("-","").replace(" ","")

def formatar_data(valor):
    """Formata data para AAMMDD. Aceita date ou string YYYY-MM-DD."""
    if hasattr(valor, 'strftime'):
        return valor.strftime("%y%m%d")
    return str(valor).replace("-","")[2:]

def formatar_hora(valor):
    """Formata hora para HHMMSS. Aceita time ou string HH:MM:SS."""
    if hasattr(valor, 'strftime'):
        return valor.strftime("%H%M%S")
    return str(valor).replace(":","")[:6]

def calcular_hash(registros_d):
    """Calcula MD5 da concatenação de todos os registros D."""
    import hashlib
    conteudo = "".join(registros_d)
    return hashlib.md5(conteudo.encode("utf-8")).hexdigest().upper()
