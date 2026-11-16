"""Peças de interface compartilhadas pelas duas telas."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import streamlit as st

from legendador import EXTENSOES_SUPORTADAS

UPLOAD = "Upload"
CAMINHO = "Caminho no disco"
ORIGENS = (UPLOAD, CAMINHO)

# Acima disso o upload começa a pesar na memória do servidor.
LIMITE_AVISO_UPLOAD = 500 * 1024 * 1024

# O tema (cores, fonte) vive em .streamlit/config.toml. Aqui ficam só os
# detalhes que o tema não alcança: gradientes, cartões e a barra lateral.
# Seletores por `data-testid` são os pontos estáveis do DOM do Streamlit.
ESTILO = """
<style>
  /* Fundo: dois brilhos suaves sobre um fundo quase preto. */
  .stApp {
    background:
      radial-gradient(1100px 420px at 50% -170px, rgba(139, 92, 246, .26), transparent 72%),
      radial-gradient(900px 380px at 100% 0%, rgba(56, 189, 248, .10), transparent 70%),
      #0b0d13;
  }

  [data-testid="stHeader"] { background: transparent; }

  [data-testid="stMainBlockContainer"] {
    max-width: 1060px;
    padding-top: 2.4rem;
    padding-bottom: 4rem;
  }

  /* Cabeçalho da página. */
  .ldr-hero h1 {
    margin: 0 0 .5rem 0;
    font-size: 2.35rem;
    font-weight: 800;
    letter-spacing: -.03em;
    line-height: 1.1;
    background: linear-gradient(96deg, #c4b5fd 0%, #ffffff 46%, #7dd3fc 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    color: transparent;
  }

  .ldr-hero p {
    margin: 0 0 1rem 0;
    max-width: 720px;
    color: #98a2b3;
    font-size: 1.02rem;
    line-height: 1.5;
  }

  .ldr-chips { display: flex; flex-wrap: wrap; gap: .5rem; }

  .ldr-chips span {
    padding: .3rem .75rem;
    font-size: .82rem;
    color: #cbd5e1;
    background: rgba(255, 255, 255, .05);
    border: 1px solid rgba(255, 255, 255, .09);
    border-radius: 999px;
  }

  /* Títulos das seções: menores que o título da página, com um fio discreto. */
  .stApp h2 {
    margin-top: .3rem !important;
    font-size: 1.55rem !important;
    font-weight: 700;
    letter-spacing: -.01em;
    border-bottom: none !important;
  }

  /* O divisor que o Streamlit desenha abaixo do título vem no azul dele. */
  hr[data-testid="stHeadingDivider"] {
    height: 1px !important;
    border: 0 !important;
    background: linear-gradient(
      90deg,
      rgba(139, 92, 246, .75),
      rgba(56, 189, 248, .30) 45%,
      rgba(255, 255, 255, 0) 100%
    ) !important;
  }

  .stApp h5 {
    margin-bottom: .35rem !important;
    color: #a5b4fc;
    font-weight: 600;
  }

  /* Métricas como cartõezinhos. */
  [data-testid="stMetric"] {
    height: 100%;
    padding: .7rem .9rem;
    background: rgba(255, 255, 255, .035);
    border: 1px solid rgba(255, 255, 255, .08);
    border-radius: 12px;
  }

  [data-testid="stMetricValue"] { font-size: 1.4rem; font-weight: 700; }

  [data-testid="stMetricLabel"] { opacity: .75; }

  /* Botões com um pouco mais de corpo. */
  .stButton > button, .stDownloadButton > button {
    border-radius: 10px;
    font-weight: 600;
    transition: transform .08s ease, box-shadow .15s ease;
  }

  .stButton > button:hover, .stDownloadButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 8px 20px rgba(0, 0, 0, .35);
  }

  /* Barra lateral. */
  [data-testid="stSidebar"] {
    background: #0f1218;
    border-right: 1px solid rgba(255, 255, 255, .06);
  }

  [data-testid="stSidebar"] [role="radiogroup"] { gap: .2rem; }

  [data-testid="stSidebar"] [role="radiogroup"] > label {
    padding: .5rem .6rem;
    border-radius: 9px;
    transition: background .12s ease;
  }

  [data-testid="stSidebar"] [role="radiogroup"] > label:hover {
    background: rgba(255, 255, 255, .05);
  }

  /* Caixas de aviso e de sucesso: fundo translúcido no tom do tipo, sem a
     barra sólida do tema padrão. O tipo vem do `data-testid` interno. */
  [data-testid="stAlert"] { border-radius: 12px; }

  [data-testid="stAlertContainer"] {
    border: 1px solid rgba(255, 255, 255, .08);
    border-radius: 12px;
    background: rgba(255, 255, 255, .035);
  }

  [data-testid="stAlert"]:has([data-testid="stAlertContentInfo"])
    [data-testid="stAlertContainer"] {
    background: rgba(56, 189, 248, .10);
    border-color: rgba(56, 189, 248, .26);
  }

  [data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"])
    [data-testid="stAlertContainer"] {
    background: rgba(34, 197, 94, .10);
    border-color: rgba(34, 197, 94, .26);
  }

  [data-testid="stAlert"]:has([data-testid="stAlertContentWarning"])
    [data-testid="stAlertContainer"] {
    background: rgba(245, 158, 11, .10);
    border-color: rgba(245, 158, 11, .28);
  }

  [data-testid="stAlert"]:has([data-testid="stAlertContentError"])
    [data-testid="stAlertContainer"] {
    background: rgba(239, 68, 68, .10);
    border-color: rgba(239, 68, 68, .28);
  }

  /* O texto do alerta vem na cor forte do tipo, pensada para fundo claro.
     Sobre o fundo escuro translúcido, o corpo usa a cor de texto do tema. */
  [data-testid="stAlertContainer"] [data-testid="stMarkdownContainer"] p,
  [data-testid="stAlertContainer"] [data-testid="stMarkdownContainer"] strong {
    color: #e2e6f0;
  }

  [data-testid="stExpander"] details {
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, .08);
    background: rgba(255, 255, 255, .02);
  }

  /* Cartões das etapas. O `key` do container vira a classe st-key-cartao_*,
     então todos os cartões compartilham uma única regra. */
  [class*="st-key-cartao_"] {
    padding: 1.15rem 1.3rem 1.35rem 1.3rem !important;
    background: linear-gradient(180deg, rgba(255, 255, 255, .045), rgba(255, 255, 255, .012));
    border: 1px solid rgba(255, 255, 255, .09) !important;
    border-radius: 16px !important;
    box-shadow: 0 12px 30px rgba(0, 0, 0, .25);
  }

  /* Título da etapa, dentro do cartão. */
  .ldr-etapa {
    margin: 0 0 .9rem 0;
    font-size: .74rem;
    font-weight: 700;
    letter-spacing: .14em;
    text-transform: uppercase;
    color: #a5b4fc;
  }

  /* Botão principal com preenchimento em degradê. */
  .stButton > button[kind="primary"],
  .stDownloadButton > button[kind="primary"] {
    padding: .55rem 1.15rem;
    background: linear-gradient(96deg, #7c3aed, #6366f1 55%, #0ea5e9);
    border: none;
    box-shadow: 0 8px 22px rgba(124, 58, 237, .35);
  }

  .stButton > button[kind="primary"]:hover,
  .stDownloadButton > button[kind="primary"]:hover {
    box-shadow: 0 12px 28px rgba(124, 58, 237, .45);
  }

  /* A pré-visualização da legenda também é um bloco de código. */
  [data-testid="stCode"] pre {
    border-radius: 12px !important;
    border: 1px solid rgba(255, 255, 255, .07) !important;
    font-size: .82rem !important;
  }

  /* Área de upload: contorno tracejado com a cor de destaque. */
  [data-testid="stFileUploaderDropzone"] {
    padding: 1rem;
    background: rgba(139, 92, 246, .06);
    border: 1px dashed rgba(139, 92, 246, .45);
    border-radius: 14px;
  }

  /* Navegação: a opção ativa ganha um realce. */
  [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
    background: rgba(139, 92, 246, .16);
    box-shadow: inset 0 0 0 1px rgba(139, 92, 246, .35);
  }

  /* Rodapé discreto no fim da página. */
  .ldr-rodape {
    margin-top: 2.6rem;
    padding-top: 1rem;
    border-top: 1px solid rgba(255, 255, 255, .07);
    font-size: .8rem;
    color: #6b7280;
    text-align: center;
  }
</style>
"""

CHIPS = ("🔒 100% local", "⚡ faster-whisper", "🎬 queima ou faixa")


def aplicar_estilo() -> None:
    """Injeta o CSS da interface. Precisa rodar em cada rerun."""
    st.markdown(ESTILO, unsafe_allow_html=True)


def cabecalho() -> None:
    """Título, subtítulo e as etiquetas do topo."""
    etiquetas = "".join(f"<span>{etiqueta}</span>" for etiqueta in CHIPS)
    st.markdown(
        f"""
        <div class="ldr-hero">
          <h1>Legendador de Vídeo e Áudio</h1>
          <p>
            Gere a legenda do seu vídeo com o Whisper e cole essa legenda de volta
            no vídeo — tudo na sua máquina, sem API e sem custo por minuto.
          </p>
          <div class="ldr-chips">{etiquetas}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@contextmanager
def cartao(chave: str, titulo: str) -> Iterator[None]:
    """Cartão com borda, fundo e o título da etapa.

    A `key` do container vira a classe `st-key-cartao_<chave>`, que o CSS usa
    para desenhar todos os cartões com uma única regra.
    """
    with st.container(border=True, key=f"cartao_{chave}"):
        st.markdown(f'<p class="ldr-etapa">{titulo}</p>', unsafe_allow_html=True)
        yield


def rodape() -> None:
    """Fecho discreto no fim da página."""
    st.markdown(
        '<p class="ldr-rodape">Tudo roda na sua máquina · SRT e VTT · '
        "queimar ou embutir</p>",
        unsafe_allow_html=True,
    )


@dataclass(frozen=True)
class Escolha:
    """Arquivo escolhido pelo usuário."""

    entrada: object
    nome: str
    chave: str
    rotulo: str
    tamanho: int = 0


def formatar_tamanho(tamanho_bytes: int) -> str:
    """Tamanho em MB ou GB — vídeo grande não deve aparecer como '3200.00 MB'."""
    megabytes = tamanho_bytes / (1024 * 1024)
    if megabytes >= 1024:
        return f"{megabytes / 1024:.2f} GB"
    return f"{megabytes:.2f} MB"


def formatar_duracao(segundos: float | None) -> str:
    if not segundos:
        return "—"
    minutos, resto = divmod(int(segundos), 60)
    return f"{minutos:02d}:{resto:02d}"


def formatar_tempo(segundos: float) -> str:
    """Timestamp legível para 'HH:MM:SS,mmm' (comum em legenda)."""
    milissegundos = max(0, int(round(segundos * 1000)))
    horas, resto = divmod(milissegundos, 3_600_000)
    minutos, resto = divmod(resto, 60_000)
    segundos_restantes, milissegundos = divmod(resto, 1000)
    return f"{horas:02d}:{minutos:02d}:{segundos_restantes:02d},{milissegundos:03d}"


def chave_do_arquivo(nome: str, dados: bytes) -> str:
    """Identidade do upload: nome + conteúdo.

    Reenviar o mesmo arquivo reaproveita o resultado; trocar o nome ou o
    conteúdo invalida o trabalho anterior.
    """
    return hashlib.sha256(nome.encode("utf-8") + dados).hexdigest()


def decodificar_texto(dados: bytes) -> str:
    """Lê um arquivo de legenda que pode estar em UTF-8 ou no antigo cp1252."""
    for codificacao in ("utf-8-sig", "cp1252"):
        try:
            return dados.decode(codificacao)
        except UnicodeDecodeError:
            continue
    return dados.decode("utf-8", errors="replace")


# --------------------------------------------------------------------------- #
# Pasta de destino
# --------------------------------------------------------------------------- #


def caminho_local(origem: object) -> Path | None:
    """Caminho em disco do arquivo escolhido — None quando ele veio por upload."""
    if isinstance(origem, (str, Path)):
        caminho = Path(origem)
        if caminho.is_file():
            return caminho
    return None


def pasta_padrao(origem: object | None = None) -> Path:
    """Pasta sugerida para os arquivos gerados.

    A regra é sempre derivada do sistema onde o app está rodando: a pasta do
    arquivo escolhido, senão a de Downloads, a de Vídeos ou a pasta do usuário.
    Não existe caminho fixo no código.
    """
    caminho = caminho_local(origem) if origem is not None else None
    if caminho is not None:
        return caminho.parent

    for nome in ("Downloads", "Videos", "Vídeos"):
        candidata = Path.home() / nome
        if candidata.is_dir():
            return candidata

    return Path.home()


def campo_pasta(
    rotulo: str,
    *,
    chave: str,
    origem: object | None = None,
    ajuda: str = "",
) -> Path | None:
    """Pede a pasta onde salvar e devolve o caminho (ou None se ainda não vale).

    Não cria a pasta: ela é criada no momento de salvar, para não deixar pastas
    vazias para trás enquanto o usuário ainda digita o caminho.
    """
    texto = (
        st.text_input(
            rotulo,
            value=str(pasta_padrao(origem)),
            key=chave,
            help=ajuda
            or "Pasta onde o arquivo será salvo. Ela é criada se não existir.",
        )
        .strip()
        .strip('"')
    )

    if not texto:
        st.info("Informe uma pasta para salvar.")
        return None

    pasta = Path(texto).expanduser()
    if pasta.exists() and not pasta.is_dir():
        st.error(f"Isto é um arquivo, não uma pasta: {pasta}")
        return None

    return pasta


# --------------------------------------------------------------------------- #
# Campos de arquivo
# --------------------------------------------------------------------------- #


def campo_arquivo(
    origem: str,
    *,
    prefixo: str,
    rotulo: str,
    tipos: tuple[str, ...] = EXTENSOES_SUPORTADAS,
) -> Escolha | None:
    """Renderiza o campo de upload ou de caminho e devolve o arquivo escolhido.

    Devolve None (já mostrando a mensagem para o usuário) quando ainda não há
    um arquivo válido.
    """
    if origem == CAMINHO:
        texto = (
            st.text_input(
                rotulo,
                placeholder="Ex.: Caminho completo até o arquivo de vídeo ou áudio",
                help="Cole o caminho completo. Aspas de 'Copiar como caminho' são aceitas.",
                key=f"caminho_{prefixo}",
            )
            .strip()
            .strip('"')
        )

        if not texto:
            st.info("Cole o caminho completo do arquivo para começar.")
            return None

        caminho = Path(texto)
        if not caminho.is_file():
            st.error(f"Arquivo não encontrado: {caminho}")
            return None

        if caminho.suffix.lower() not in tipos:
            aceitas = ", ".join(tipos)
            st.error(
                f"Formato '{caminho.suffix}' não suportado. Use um destes: {aceitas}."
            )
            return None

        detalhes = caminho.stat()
        return Escolha(
            entrada=caminho,
            nome=caminho.name,
            chave=(
                f"caminho::{caminho.resolve()}::{detalhes.st_size}"
                f"::{detalhes.st_mtime_ns}"
            ),
            rotulo=(
                f"**{caminho.name}** · {formatar_tamanho(detalhes.st_size)}"
                " · lido direto do disco"
            ),
            tamanho=detalhes.st_size,
        )

    limite = st.config.get_option("server.maxUploadSize")
    st.caption(
        f"Limite do upload: **{limite} MB**. Para arquivos maiores, use "
        "**Caminho no disco** — o arquivo é lido direto do seu computador."
    )

    arquivo = st.file_uploader(
        rotulo,
        type=[extensao.lstrip(".") for extensao in tipos],
        key=f"upload_{prefixo}",
    )

    if arquivo is None:
        st.info("Envie um arquivo para começar.")
        return None

    dados = arquivo.getvalue()

    if len(dados) > LIMITE_AVISO_UPLOAD:
        st.warning(
            "Arquivo grande: pelo navegador, o arquivo inteiro fica na memória. "
            "O modo **Caminho no disco** é mais rápido e bem mais leve."
        )

    return Escolha(
        entrada=arquivo,
        nome=arquivo.name,
        chave=chave_do_arquivo(arquivo.name, dados),
        rotulo=f"**{arquivo.name}** · {formatar_tamanho(len(dados))}",
        tamanho=len(dados),
    )
