from datetime import datetime
from decimal import Decimal, InvalidOperation

from . import banco
from .config import TAMANHO_BLOCO


# ---------------------------------------------------------------------------
# Funcoes de conversao de tipo
# ---------------------------------------------------------------------------
def texto_para_decimal(valor):
    """Converte '1.272,97' / '1272,97' / '' -> Decimal. Retorna None se vazio
    ou invalido (nunca lanca excecao para nao interromper o lote)."""
    if valor is None:
        return None
    valor = str(valor).strip()
    if valor == "" or valor.lower() == "sem informação":
        return None
    try:
        valor_normalizado = valor.replace(".", "").replace(",", ".")
        return Decimal(valor_normalizado)
    except InvalidOperation:
        return None


def texto_para_data(valor):
    """Converte 'DD/MM/AAAA' -> date. Retorna None se vazio ou invalido."""
    if valor is None:
        return None
    valor = str(valor).strip()
    if valor == "" or valor.lower() == "sem informação":
        return None
    try:
        return datetime.strptime(valor, "%d/%m/%Y").date()
    except ValueError:
        return None


def texto_para_int(valor):
    """Converte texto numerico simples -> int. Retorna None se invalido."""
    if valor is None:
        return None
    valor = str(valor).strip()
    if valor == "":
        return None
    try:
        return int(Decimal(valor.replace(",", ".")))
    except InvalidOperation:
        return None


# ---------------------------------------------------------------------------
# Utilitario: le uma tabela em blocos (paginada por LIMIT/OFFSET)
# ---------------------------------------------------------------------------
def ler_em_blocos(conexao, sql_base, tamanho_bloco=TAMANHO_BLOCO):
    offset = 0
    cursor = conexao.cursor(dictionary=True)
    while True:
        cursor.execute(f"{sql_base} LIMIT {tamanho_bloco} OFFSET {offset}")
        linhas = cursor.fetchall()
        if not linhas:
            break
        yield linhas
        offset += tamanho_bloco
    cursor.close()


# ---------------------------------------------------------------------------
# silver_viagem
# ---------------------------------------------------------------------------
def transformar_viagem(conexao):
    banco.executar(conexao, "TRUNCATE TABLE silver_viagem;")

    sql_insert = """
        INSERT INTO silver_viagem (
            id_viagem, num_proposta, situacao, viagem_urgente, cod_orgao_superior,
            nome_orgao_superior, nome_viajante, cargo, data_inicio, data_fim,
            destinos, motivo, valor_diarias, valor_passagens, valor_devolucao,
            valor_outros_gastos, valor_total, duracao_dias
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    total_ok, total_descartadas = 0, 0
    ids_validos = set()

    for bloco in ler_em_blocos(conexao, "SELECT * FROM raw_viagem"):
        linhas = []
        for linha in bloco:
            id_viagem = (linha["id_viagem"] or "").strip()
            nome_orgao_superior = (linha["nome_orgao_superior"] or "").strip()

            if not id_viagem or not nome_orgao_superior:
                total_descartadas += 1
                continue
            if id_viagem in ids_validos:
                total_descartadas += 1
                continue

            data_inicio = texto_para_data(linha["data_inicio"])
            data_fim = texto_para_data(linha["data_fim"])
            valor_diarias = texto_para_decimal(linha["valor_diarias"]) or Decimal("0")
            valor_passagens = texto_para_decimal(linha["valor_passagens"]) or Decimal("0")
            valor_devolucao = texto_para_decimal(linha["valor_devolucao"]) or Decimal("0")
            valor_outros_gastos = texto_para_decimal(linha["valor_outros_gastos"]) or Decimal("0")

            valor_total = valor_diarias + valor_passagens + valor_devolucao + valor_outros_gastos
            duracao_dias = (data_fim - data_inicio).days if (data_inicio and data_fim) else None

            linhas.append((
                id_viagem,
                linha["num_proposta"],
                linha["situacao"],
                linha["viagem_urgente"],
                linha["cod_orgao_superior"],
                nome_orgao_superior,
                linha["nome_viajante"],
                linha["cargo"],
                data_inicio,
                data_fim,
                linha["destinos"],
                linha["motivo"],
                valor_diarias,
                valor_passagens,
                valor_devolucao,
                valor_outros_gastos,
                valor_total,
                duracao_dias,
            ))
            ids_validos.add(id_viagem)

        if linhas:
            banco.inserir_em_lote(conexao, sql_insert, linhas)
            total_ok += len(linhas)

    print(f"[OK] silver_viagem: {total_ok} linhas carregadas, {total_descartadas} descartadas.")
    return ids_validos


# ---------------------------------------------------------------------------
# silver_pagamento
# ---------------------------------------------------------------------------
def transformar_pagamento(conexao, ids_validos):
    banco.executar(conexao, "TRUNCATE TABLE silver_pagamento;")

    sql_insert = """
        INSERT INTO silver_pagamento (
            id_viagem, num_proposta, nome_orgao_pagador, nome_ug_pagadora,
            tipo_pagamento, valor
        ) VALUES (%s, %s, %s, %s, %s, %s)
    """

    total_ok, total_descartadas = 0, 0
    for bloco in ler_em_blocos(conexao, "SELECT * FROM raw_pagamento"):
        linhas = []
        for linha in bloco:
            id_viagem = (linha["id_viagem"] or "").strip()
            tipo_pagamento = (linha["tipo_pagamento"] or "").strip()
            valor = texto_para_decimal(linha["valor"])

            if id_viagem not in ids_validos or not tipo_pagamento or valor is None or valor < 0:
                total_descartadas += 1
                continue

            linhas.append((
                id_viagem,
                linha["num_proposta"],
                linha["nome_orgao_pagador"],
                linha["nome_ug_pagadora"],
                tipo_pagamento,
                valor,
            ))

        if linhas:
            banco.inserir_em_lote(conexao, sql_insert, linhas)
            total_ok += len(linhas)

    print(f"[OK] silver_pagamento: {total_ok} linhas carregadas, {total_descartadas} descartadas.")


# ---------------------------------------------------------------------------
# silver_passagem
# ---------------------------------------------------------------------------
def transformar_passagem(conexao, ids_validos):
    banco.executar(conexao, "TRUNCATE TABLE silver_passagem;")

    sql_insert = """
        INSERT INTO silver_passagem (
            id_viagem, meio_transporte, pais_origem_ida, uf_origem_ida,
            cidade_origem_ida, pais_destino_ida, uf_destino_ida,
            cidade_destino_ida, valor_passagem, taxa_servico, data_emissao
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    total_ok, total_descartadas = 0, 0
    for bloco in ler_em_blocos(conexao, "SELECT * FROM raw_passagem"):
        linhas = []
        for linha in bloco:
            id_viagem = (linha["id_viagem"] or "").strip()
            valor_passagem = texto_para_decimal(linha["valor_passagem"]) or Decimal("0")
            taxa_servico = texto_para_decimal(linha["taxa_servico"]) or Decimal("0")

            if id_viagem not in ids_validos or valor_passagem < 0 or taxa_servico < 0:
                total_descartadas += 1
                continue

            linhas.append((
                id_viagem,
                linha["meio_transporte"],
                linha["pais_origem_ida"],
                linha["uf_origem_ida"],
                linha["cidade_origem_ida"],
                linha["pais_destino_ida"],
                linha["uf_destino_ida"],
                linha["cidade_destino_ida"],
                valor_passagem,
                taxa_servico,
                texto_para_data(linha["data_emissao"]),
            ))

        if linhas:
            banco.inserir_em_lote(conexao, sql_insert, linhas)
            total_ok += len(linhas)

    print(f"[OK] silver_passagem: {total_ok} linhas carregadas, {total_descartadas} descartadas.")


# ---------------------------------------------------------------------------
# silver_trecho
# ---------------------------------------------------------------------------
def transformar_trecho(conexao, ids_validos):
    banco.executar(conexao, "TRUNCATE TABLE silver_trecho;")

    sql_insert = """
        INSERT INTO silver_trecho (
            id_viagem, sequencia_trecho, origem_data, origem_uf, origem_cidade,
            destino_data, destino_uf, destino_cidade, meio_transporte, numero_diarias
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    total_ok, total_descartadas = 0, 0
    sequencias_vistas = set()

    for bloco in ler_em_blocos(conexao, "SELECT * FROM raw_trecho"):
        linhas = []
        for linha in bloco:
            id_viagem = (linha["id_viagem"] or "").strip()
            sequencia_trecho = texto_para_int(linha["sequencia_trecho"])
            numero_diarias = texto_para_decimal(linha["numero_diarias"]) or Decimal("0")

            chave_unica = (id_viagem, sequencia_trecho)
            if (
                id_viagem not in ids_validos
                or numero_diarias < 0
                or chave_unica in sequencias_vistas
            ):
                total_descartadas += 1
                continue

            linhas.append((
                id_viagem,
                sequencia_trecho,
                texto_para_data(linha["origem_data"]),
                linha["origem_uf"],
                linha["origem_cidade"],
                texto_para_data(linha["destino_data"]),
                linha["destino_uf"],
                linha["destino_cidade"],
                linha["meio_transporte"],
                numero_diarias,
            ))
            sequencias_vistas.add(chave_unica)

        if linhas:
            banco.inserir_em_lote(conexao, sql_insert, linhas)
            total_ok += len(linhas)

    print(f"[OK] silver_trecho: {total_ok} linhas carregadas, {total_descartadas} descartadas.")


# ---------------------------------------------------------------------------
# Orquestracao
# ---------------------------------------------------------------------------
def executar_limpeza():
    """Roda a Fase 2 completa: Raw -> Silver, na ordem correta (silver_viagem
    primeiro, pois as demais tabelas tem FK para ela). Pode ser chamada tanto
    pelo notebook quanto via `python -m src.limpeza`."""
    print("=== Fase 2: Limpeza/Transformacao e camada Silver ===")

    conexao = banco.conectar()
    try:
        ids_validos = transformar_viagem(conexao)
        transformar_pagamento(conexao, ids_validos)
        transformar_passagem(conexao, ids_validos)
        transformar_trecho(conexao, ids_validos)
    finally:
        conexao.close()

    print("=== Fase 2 concluida com sucesso ===")


if __name__ == "__main__":
    executar_limpeza()
