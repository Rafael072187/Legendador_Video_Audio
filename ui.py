"""Peças de interface compartilhadas pelas duas telas."""

from __future__ import annotations

import hashlib
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
    margin: 0 0 .4rem 0;
    font-size: 2.6rem;
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

  /* Títulos das seções: a régua vira um fio discreto. */
  .stApp h2 {
    border-bottom: 1px solid rgba(255, 255, 255, .08) !important;
    padding-bottom: .45rem !important;
    font-weight: 700;
    letter-spacing: -.01em;
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

  /* Caixas de aviso e de sucesso com cantos redondos. */
  [data-testid="stAlert"] { border-radius: 12px; }

  [data-testid="stExpander"] details {
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, .08);
    background: rgba(255, 255, 255, .02);
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
                placeholder=r"C:\Users\SeuUsuario\Videos\video.mp4",
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
