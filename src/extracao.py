import zipfile

import gdown
import pandas as pd

from . import banco
from .config import (
    ARQUIVOS,
    CSV_ENCODING,
    CSV_SEPARADOR,
    DRIVE_FILE_ID,
    PASTA_DADOS_RAW,
    TAMANHO_BLOCO,
)

NOME_ZIP = PASTA_DADOS_RAW / "viagens_2025.zip"



COLUNAS_RAW = {
    "viagem": {
        "Identificador do processo de viagem": "id_viagem",
        "Número da Proposta (PCDP)": "num_proposta",
        "Situação": "situacao",
        "Viagem Urgente": "viagem_urgente",
        "Justificativa Urgência Viagem": "justificativa_urgencia",
        "Código do órgão superior": "cod_orgao_superior",
        "Nome do órgão superior": "nome_orgao_superior",
        "Código órgão solicitante": "cod_orgao_solicitante",
        "Nome órgão solicitante": "nome_orgao_solicitante",
        "CPF viajante": "cpf_viajante",
        "Nome": "nome_viajante",
        "Cargo": "cargo",
        "Função": "funcao",
        "Descrição Função": "descricao_funcao",
        "Período - Data de início": "data_inicio",
        "Período - Data de fim": "data_fim",
        "Destinos": "destinos",
        "Motivo": "motivo",
        "Valor diárias": "valor_diarias",
        "Valor passagens": "valor_passagens",
        "Valor devolução": "valor_devolucao",
        "Valor outros gastos": "valor_outros_gastos",
    },
    "pagamento": {
        "Identificador do processo de viagem": "id_viagem",
        "Número da Proposta (PCDP)": "num_proposta",
        "Código do órgão superior": "cod_orgao_superior",
        "Nome do órgão superior": "nome_orgao_superior",
        "Codigo do órgão pagador": "cod_orgao_pagador",
        "Nome do órgao pagador": "nome_orgao_pagador",
        "Código da unidade gestora pagadora": "cod_ug_pagadora",
        "Nome da unidade gestora pagadora": "nome_ug_pagadora",
        "Tipo de pagamento": "tipo_pagamento",
        "Valor": "valor",
    },
    "passagem": {
        "Identificador do processo de viagem": "id_viagem",
        "Número da Proposta (PCDP)": "num_proposta",
        "Meio de transporte": "meio_transporte",
        "País - Origem ida": "pais_origem_ida",
        "UF - Origem ida": "uf_origem_ida",
        "Cidade - Origem ida": "cidade_origem_ida",
        "País - Destino ida": "pais_destino_ida",
        "UF - Destino ida": "uf_destino_ida",
        "Cidade - Destino ida": "cidade_destino_ida",
        "País - Origem volta": "pais_origem_volta",
        "UF - Origem volta": "uf_origem_volta",
        "Cidade - Origem volta": "cidade_origem_volta",
        "Pais - Destino volta": "pais_destino_volta",
        "UF - Destino volta": "uf_destino_volta",
        "Cidade - Destino volta": "cidade_destino_volta",
        "Valor da passagem": "valor_passagem",
        "Taxa de serviço": "taxa_servico",
        "Data da emissão/compra": "data_emissao",
        "Hora da emissão/compra": "hora_emissao",
    },
    "trecho": {
        "Identificador do processo de viagem ": "id_viagem",
        "Número da Proposta (PCDP)": "num_proposta",
        "Sequência Trecho": "sequencia_trecho",
        "Origem - Data": "origem_data",
        "Origem - País": "origem_pais",
        "Origem - UF": "origem_uf",
        "Origem - Cidade": "origem_cidade",
        "Destino - Data": "destino_data",
        "Destino - País": "destino_pais",
        "Destino - UF": "destino_uf",
        "Destino - Cidade": "destino_cidade",
        "Meio de transporte": "meio_transporte",
        "Número Diárias": "numero_diarias",
        "Missao?": "missao",
    },
}


# ---------------------------------------------------------------------------
# Etapa 1: download do .zip no Google Drive
# ---------------------------------------------------------------------------
def baixar_zip_do_drive():
    """Baixa o .zip do Google Drive para data/raw/ usando gdown, que ja
    trata sozinho o token de confirmacao exigido pelo Drive para arquivos
    grandes (aviso de virus/verificacao)."""
    PASTA_DADOS_RAW.mkdir(parents=True, exist_ok=True)

    if DRIVE_FILE_ID.startswith("COLE_AQUI"):
        raise RuntimeError(
            "DRIVE_FILE_ID nao configurado. Edite src/config.py e cole o ID "
            "do arquivo do Google Drive antes de rodar a extracao."
        )

    url = f"https://drive.google.com/uc?id={DRIVE_FILE_ID}"

    try:
        caminho_baixado = gdown.download(url, str(NOME_ZIP), quiet=False)
        if not caminho_baixado:
            raise RuntimeError("gdown nao retornou um arquivo baixado.")

        print(f"[OK] Download concluido: {NOME_ZIP}")

    except Exception as erro:
        raise RuntimeError(f"Falha ao baixar o .zip do Google Drive: {erro}")


# ---------------------------------------------------------------------------
# Etapa 2: leitura em blocos + carga na tabela Raw
# ---------------------------------------------------------------------------
def carregar_tabela_raw(conexao, chave, nome_csv_no_zip):
    """Le um CSV (de dentro do .zip) em blocos e carrega na tabela Raw,
    sem alterar o conteudo original."""
    tabela_raw = ARQUIVOS[chave]["tabela_raw"]
    mapa_colunas = COLUNAS_RAW[chave]
    colunas_finais = list(mapa_colunas.values())

    placeholders = ", ".join(["%s"] * len(colunas_finais))
    colunas_sql = ", ".join(colunas_finais)
    sql_insert = f"INSERT INTO {tabela_raw} ({colunas_sql}) VALUES ({placeholders})"

    # Idempotencia: garante que reexecutar a extracao nao duplica dados
    banco.executar(conexao, f"TRUNCATE TABLE {tabela_raw};")

    total_linhas = 0
    try:
        with zipfile.ZipFile(NOME_ZIP) as zip_arquivo:
            with zip_arquivo.open(nome_csv_no_zip) as csv_arquivo:
                leitor = pd.read_csv(
                    csv_arquivo,
                    sep=CSV_SEPARADOR,
                    encoding=CSV_ENCODING,
                    dtype=str,
                    keep_default_na=False,
                    chunksize=TAMANHO_BLOCO,
                )
                for bloco in leitor:
                    bloco = bloco.rename(columns=mapa_colunas)
                    bloco = bloco[colunas_finais]
                    linhas = [tuple(linha) for linha in bloco.itertuples(index=False, name=None)]
                    banco.inserir_em_lote(conexao, sql_insert, linhas)
                    total_linhas += len(linhas)

        print(f"[OK] {tabela_raw}: {total_linhas} linhas carregadas.")

    except (FileNotFoundError, KeyError, zipfile.BadZipFile, pd.errors.ParserError) as erro:
        raise RuntimeError(f"Falha ao carregar {tabela_raw} a partir de {nome_csv_no_zip}: {erro}")


# ---------------------------------------------------------------------------
# Orquestracao
# ---------------------------------------------------------------------------
def executar_extracao():
    """Roda a Fase 1 completa: baixa o zip (se necessario) e carrega as
    4 tabelas Raw. Pode ser chamada tanto pelo notebook quanto via
    `python -m src.extracao`."""
    print("=== Fase 1: Extracao e camada Raw ===")

    if not NOME_ZIP.exists():
        baixar_zip_do_drive()
    else:
        print(f"[INFO] Zip ja existe em {NOME_ZIP}, pulando o download.")

    conexao = banco.conectar()
    try:
        for chave, info in ARQUIVOS.items():
            carregar_tabela_raw(conexao, chave, info["csv"])
    finally:
        conexao.close()

    print("=== Fase 1 concluida com sucesso ===")


if __name__ == "__main__":
    executar_extracao()
