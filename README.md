Como executar

Pré-requisitos
- Python 3.10+
- MySQL Server 8.0+ em execução
- Um arquivo `.zip` com os 4 CSVs (`2025_Viagem.csv`, `2025_Pagamento.csv`, `2025_Passagem.csv`, `2025_Trecho.csv`) hospedado no Google Drive, com compartilhamento "qualquer pessoa com o link"

Passo a passo

```bash
# 1. Clonar o repositório e entrar na pasta
git clone <url-do-repositorio>
cd desafio_transparencia

# 2. Criar e ativar um ambiente virtual (recomendado)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Instalar as dependências
pip install -r requirements.txt

# 4. Configurar as credenciais
cp .env.example .env
# edite o .env com host/usuário/senha do seu MySQL

# 5. Colar o ID do arquivo do Google Drive em src/config.py
# (a parte "id=" da URL de compartilhamento do Drive)
# DRIVE_FILE_ID = "SEU_ID_AQUI"

# 6. Criar o banco e as 8 tabelas
mysql -u root -p < sql/0_criar_banco.sql

# 7. Rodar os notebooks, nessa ordem
jupyter notebook notebooks/01_exploracao.ipynb    # baixa o zip e carrega a Raw
jupyter notebook notebooks/02_limpeza.ipynb       # Raw -> Silver
jupyter notebook notebooks/03_visualizacao.ipynb  # Silver -> Gold, perguntas,
```

Cada notebook também pode ser rodado via linha de comando, sem abrir o
Jupyter, chamando diretamente as funções de `src/`:

```bash
python -m src.extracao     # equivalente a rodar o notebook 01
python -m src.limpeza      # equivalente a rodar o notebook 02
```

O pipeline é idempotente: rodar `src.extracao` e `src.limpeza` várias vezes não duplica dados (cada um faz `TRUNCATE` na tabela de destino antes de carregar) — e resiliente: falhas de download, leitura ou carga são capturadas com `try/except` e reportadas com uma mensagem clara.

Ferramentas utilizadas

- Python 3 — extração (`pandas` + `gdown`), transformação e carga
- MySQL — armazenamento das camadas Raw, Silver e Gold
- pandas — leitura dos CSVs em blocos (chunks) e consultas na camada Gold
- matplotlib — visualização de dados
- Jupyter Notebook — os 3 notebooks numerados em `notebooks/`
- Arquitetura Medallion — Raw (dado bruto) → Silver (dado limpo e tipado, com integridade referencial) → Gold (métricas agregadas prontas para consumo)

Conclusões e insights

- Os órgãos com maior custo total de viagens tendem a ser aqueles com operações descentralizadas por todo o território nacional (segurança pública, defesa, educação).
- O custo médio por viagem varia bastante por destino, com destaque para viagens que envolvem múltiplos trechos/cidades.
- Diárias e passagens concentram os maiores valores médios de pagamento, o que é esperado por serem os itens de maior custo unitário de uma viagem a serviço.
- Veículo oficial supera o transporte aéreo em quantidade de trechos, sugerindo um volume relevante de deslocamentos regionais de curta distância.
- Unidades federativas com grande estrutura administrativa federal concentram a maior parte dos trechos de destino.

A análise completa, com as consultas SQL, tabelas e gráficos que embasam cada
um desses pontos, está em [`notebooks/03_visualizacao.ipynb`](./notebooks/03_visualizacao.ipynb)
