import xmlschema
from lxml import etree
import os
import sys
import time

# Obtém o diretório onde este script está localizado
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def validar_com_xmlschema(xml_file, xsd_file):
    """
    Valida um arquivo XML usando a biblioteca xmlschema.
    Retorna True se for válido, False caso contrário, e imprime os erros.
    """
    try:
        schema = xmlschema.XMLSchema(xsd_file)
        schema.validate(xml_file)  # valida diretamente; lança exceção se inválido
        print(f"✅ {xml_file} é válido segundo o schema.")
        return True
    except xmlschema.XMLSchemaException as e:
        # Se for erro de validação, imprime detalhes
        print(f"❌ Erro de validação em {xml_file}:")
        # xmlschema pode retornar uma lista de erros
        if hasattr(e, 'errors'):
            for err in e.errors:
                print(f"   - {err}")
        else:
            print(f"   {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado em {xml_file}: {e}")
        return False

def validar_com_lxml(xml_file, xsd_file):
    """
    Valida um arquivo XML usando lxml.
    Retorna True se válido, False caso contrário, e imprime os erros.
    """
    try:
        # Carrega o schema XSD
        with open(xsd_file, 'rb') as f:
            schema_root = etree.XML(f.read())
        schema = etree.XMLSchema(schema_root)

        # Carrega e valida o XML
        xml_doc = etree.parse(xml_file)
        if schema.validate(xml_doc):
            print(f"✅ {xml_file} é válido segundo o schema (lxml).")
            return True
        else:
            # Exibe os erros
            log = schema.error_log
            print(f"❌ Erro de validação em {xml_file}:")
            for error in log:
                print(f"   - Linha {error.line}, coluna {error.column}: {error.message}")
            return False
    except etree.XMLSyntaxError as e:
        print(f"❌ Erro de sintaxe XML em {xml_file}: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado em {xml_file}: {e}")
        return False

def main():
    # Define os caminhos usando SCRIPT_DIR (pasta onde o script está)
    xsd_file = os.path.join(SCRIPT_DIR, "hospital.xsd")
    xml_files = [
        os.path.join(SCRIPT_DIR, "prescricao.xml"),
        os.path.join(SCRIPT_DIR, "encerramento.xml"),
        os.path.join(SCRIPT_DIR, "retorno_estoque.xml")
    ]

    # Verifica se o XSD existe
    if not os.path.exists(xsd_file):
        print(f"Arquivo XSD não encontrado: {xsd_file}")
        sys.exit(1)

    print("=== Validação usando xmlschema ===")
    times_xmlschema = []
    for xml_file in xml_files:
        if os.path.exists(xml_file):
            start = time.perf_counter()
            validar_com_xmlschema(xml_file, xsd_file)
            elapsed = time.perf_counter() - start
            times_xmlschema.append(elapsed)
            print(f"   Tempo: {elapsed:.4f} segundos")
        else:
            print(f"Arquivo {xml_file} não encontrado. Pulando.")

    print("\n=== Validação usando lxml ===")
    times_lxml = []
    for xml_file in xml_files:
        if os.path.exists(xml_file):
            start = time.perf_counter()
            validar_com_lxml(xml_file, xsd_file)
            elapsed = time.perf_counter() - start
            times_lxml.append(elapsed)
            print(f"   Tempo: {elapsed:.4f} segundos")
        else:
            print(f"Arquivo {xml_file} não encontrado. Pulando.")

    # Resumo
    if times_xmlschema:
        print(f"\n--- Resumo xmlschema ---")
        print(f"Total de arquivos: {len(times_xmlschema)}")
        print(f"Tempo total: {sum(times_xmlschema):.4f} segundos")
        print(f"Tempo médio: {sum(times_xmlschema)/len(times_xmlschema):.4f} segundos")
    if times_lxml:
        print(f"\n--- Resumo lxml ---")
        print(f"Total de arquivos: {len(times_lxml)}")
        print(f"Tempo total: {sum(times_lxml):.4f} segundos")
        print(f"Tempo médio: {sum(times_lxml)/len(times_lxml):.4f} segundos")

if __name__ == "__main__":
    main()