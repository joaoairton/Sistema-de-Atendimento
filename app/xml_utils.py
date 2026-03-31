import dicttoxml
from xml.dom import minidom

def dict_to_xml(data: dict, root_name: str = "root") -> str:
    xml_bytes = dicttoxml.dicttoxml(data, custom_root=root_name, attr_type=False)
    dom = minidom.parseString(xml_bytes)
    return dom.toprettyxml(indent="  ")

def atendimento_to_dict(atendimento) -> dict:
    """Converte um objeto Atendimento para dicionário (com tratamento de None)"""
    d = {
        "id_atendimento": atendimento.id_atendimento,
        "cpf_paciente": atendimento.cpf_paciente,
        "data_abertura": str(atendimento.data_abertura) if atendimento.data_abertura else None,
        "hora_abertura": str(atendimento.hora_abertura) if atendimento.hora_abertura else None,
        "tipo": atendimento.tipo,
        "crm_medico": atendimento.crm_medico,
        "especialidade": atendimento.especialidade,
        "convenio": atendimento.convenio,
        "carteirinha": atendimento.carteirinha,
        "status": atendimento.status,
        "observacao": atendimento.observacao,
        "data_encerramento": str(atendimento.data_encerramento) if atendimento.data_encerramento else None,
        "hora_encerramento": str(atendimento.hora_encerramento) if atendimento.hora_encerramento else None,
        "cid_principal": atendimento.cid_principal,
        "procedimento": atendimento.procedimento,
        "qtd_medicamentos": atendimento.qtd_medicamentos,
        "valor_procedimentos": str(atendimento.valor_procedimentos) if atendimento.valor_procedimentos else None,
    }
    # Remove campos None
    return {k: v for k, v in d.items() if v is not None}



# Adicione:
def prescricao_to_dict(prescricao) -> dict:
    d = {
        "id_prescricao": prescricao.id_prescricao,
        "id_atendimento": prescricao.id_atendimento,
        "cpf_paciente": prescricao.cpf_paciente,
        "data_prescricao": str(prescricao.data_prescricao) if prescricao.data_prescricao else None,
        "hora_prescricao": str(prescricao.hora_prescricao) if prescricao.hora_prescricao else None,
        "crm_medico": prescricao.crm_medico,
        "codigo_medicamento": prescricao.codigo_medicamento,
        "quantidade": str(prescricao.quantidade) if prescricao.quantidade is not None else None,
        "unidade_medida": prescricao.unidade_medida,
        "observacao": prescricao.observacao,
        "status_estoque": prescricao.status_estoque,
    }
    return {k: v for k, v in d.items() if v is not None}