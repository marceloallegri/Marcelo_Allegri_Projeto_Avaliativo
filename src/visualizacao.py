import matplotlib.pyplot as plt

from .config import PASTA_FIGURES

PASTA_FIGURES.mkdir(parents=True, exist_ok=True)

CORES = {
    "azul": "#2E5090",
    "vermelho": "#C0392B",
    "verde": "#1E8449",
    "roxo": "#7D3C98",
    "laranja": "#D68910",
    "azul_escuro": "#2874A6",
    "vinho": "#922B21",
}


def _salvar(nome_arquivo):
    caminho = PASTA_FIGURES / f"{nome_arquivo}.png"
    plt.tight_layout()
    plt.savefig(caminho, dpi=150)
    print(f"[OK] Figura salva em {caminho}")


def grafico_barras_horizontal(rotulos, valores, titulo, rotulo_x, cor="azul", nome_arquivo=None):
    """Grafico de barras horizontais (bom para rankings com nomes longos,
    ex.: nome de orgaos)."""
    plt.figure(figsize=(9, 5))
    plt.barh(rotulos, valores, color=CORES.get(cor, cor))
    plt.xlabel(rotulo_x)
    plt.title(titulo)
    plt.gca().invert_yaxis()
    if nome_arquivo:
        _salvar(nome_arquivo)
    plt.show()


def grafico_barras_vertical(rotulos, valores, titulo, rotulo_y, cor="azul", nome_arquivo=None):
    """Grafico de barras verticais (bom para poucas categorias, ex.:
    tipo de pagamento, meio de transporte, UF)."""
    plt.figure(figsize=(8, 5))
    plt.bar(rotulos, valores, color=CORES.get(cor, cor))
    plt.ylabel(rotulo_y)
    plt.title(titulo)
    plt.xticks(rotation=20, ha="right")
    if nome_arquivo:
        _salvar(nome_arquivo)
    plt.show()


def grafico_valor_unico(rotulo, valor, titulo, rotulo_y, cor="verde", nome_arquivo=None):
    """Grafico de uma unica barra (bom para destacar um numero isolado,
    ex.: a viagem de maior duracao)."""
    plt.figure(figsize=(5, 5))
    plt.bar([rotulo], [valor], color=CORES.get(cor, cor))
    plt.title(titulo)
    plt.ylabel(rotulo_y)
    if nome_arquivo:
        _salvar(nome_arquivo)
    plt.show()
