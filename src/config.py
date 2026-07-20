import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Caminhos do projeto
# ---------------------------------------------------------------------------
# Este arquivo mora em src/, entao a raiz do projeto e um nivel acima.
PASTA_RAIZ = Path(__file__).resolve().parent.parent

PASTA_DADOS_RAW = PASTA_RAIZ / "data" / "raw"          
PASTA_DADOS_PROCESSED = PASTA_RAIZ / "data" / "processed" 
PASTA_DADOS_EXTERNAL = PASTA_RAIZ / "data" / "external"   
PASTA_REPORTS = PASTA_RAIZ / "reports"
PASTA_FIGURES = PASTA_REPORTS / "figures"                 

# ---------------------------------------------------------------------------
# Leitura simples do arquivo .env (sem biblioteca externa)
# ---------------------------------------------------------------------------
def carregar_env():
    """Le o arquivo .env (na raiz do projeto), se existir, e joga as
    variaveis para os.environ."""
    arquivo_env = PASTA_RAIZ / ".env"
    if not arquivo_env.exists():
        return
    for linha in arquivo_env.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        # ignora linhas vazias e comentarios
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip())


carregar_env()


# ---------------------------------------------------------------------------
# Credenciais do MySQL (vem do .env)
# ---------------------------------------------------------------------------
MYSQL_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", ""),
    "database": os.environ.get("MYSQL_DATABASE", "transparencia"),
}


# ---------------------------------------------------------------------------
# O que vamos baixar e processar
# ---------------------------------------------------------------------------
ANO = "2025"

# ---- De onde baixar o .zip ----
DRIVE_FILE_ID = "1s9PEJJSWQds4qcs3x61cfGxA1WA15Ffm?usp=drive_link"

# Tamanho do bloco de leitura/insercao (numero de linhas por vez)
TAMANHO_BLOCO = 50_000

# ---------------------------------------------------------------------------
# Mapeamento: cada arquivo CSV dentro do .zip -> tabela RAW correspondente
# (o nome do CSV usa o ANO como prefixo, ex.: 2025_Viagem.csv)
# ---------------------------------------------------------------------------
ARQUIVOS = {
    "viagem":     {"csv": f"{ANO}_Viagem.csv",     "tabela_raw": "raw_viagem"},
    "pagamento":  {"csv": f"{ANO}_Pagamento.csv",  "tabela_raw": "raw_pagamento"},
    "passagem":   {"csv": f"{ANO}_Passagem.csv",   "tabela_raw": "raw_passagem"},
    "trecho":     {"csv": f"{ANO}_Trecho.csv",     "tabela_raw": "raw_trecho"},
}

# Caracteristicas dos arquivos CSV do Portal da Transparencia:
CSV_SEPARADOR = ";"
CSV_ENCODING = "latin-1"   # acentuacao no padrao ISO-8859-1
