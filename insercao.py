"""
Colocar uma legenda dentro de um vídeo.

Dois modos, ambos locais e gratuitos (só o ffmpeg):

- **queimar** (hardsub): o texto vira pixel no vídeo. Funciona em qualquer
  player, celular e rede social. Reencoda o vídeo, então é mais lento.
- **embutir** (softsub): a legenda entra como uma faixa selecionável. Não
  reencoda nada, então é quase instantâneo, mas o player precisa permitir
  ligar a faixa.

Sincronia: o SRT é aplicado na linha do tempo original do vídeo, sem
deslocamento. Quando a legenda vem do próprio vídeo (extraída por este
projeto), os tempos são os do arquivo, então o texto aparece no lugar certo
por construção — não por ajuste.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from legendador import (
    ErroLegendagem,
    duracao_segundos,
    entrada_local,
    ffmpeg_disponivel,
    nome_original,
)

MODO_QUEIMAR = "queimar"
MODO_EMBUTIR = "embutir"
MODOS = (MODO_QUEIMAR, MODO_EMBUTIR)

ROTULOS_MODOS = {
    MODO_QUEIMAR: "Queimar no vídeo (funciona em qualquer player)",
    MODO_EMBUTIR: "Embutir como faixa (rápido, liga no player)",
}

Progresso = Callable[[str], None]

# Qualidade do vídeo reencodado no modo "queimar".
CRF = "20"
PRESET = "veryfast"
BITRATE_AUDIO = "192k"


@dataclass(frozen=True)
class ResultadoInsercao:
    """Resultado de uma inserção bem-sucedida."""

    caminho: Path
    modo: str
    duracao_segundos: float | None
    tempo: float
    faixas_de_legenda: tuple[str, ...] = ()

    @property
    def tamanho_bytes(self) -> int:
        return self.caminho.stat().st_size

    @property
    def nome(self) -> str:
        return self.caminho.name


# --------------------------------------------------------------------------- #
# Nomes e destinos
# --------------------------------------------------------------------------- #


def destino_padrao(video: object, modo: str = MODO_QUEIMAR) -> Path:
    """Onde salvar o resultado quando o usuário não escolhe.

    Ao lado do vídeo original, com sufixo `_legendado` — nada é sobrescrito.
    """
    nome = nome_original(video)
    sufixo = "_legendado" if modo == MODO_QUEIMAR else "_comlegenda"

    if isinstance(video, (str, Path)):
        pasta = Path(video).expanduser().resolve().parent
    else:
        pasta = Path.home() / "Downloads"
        if not pasta.is_dir():
            pasta = Path.home()

    return pasta / f"{Path(nome).stem}{sufixo}.mp4"


def _validar_saida(destino: Path, video: object) -> Path:
    """O destino precisa ser um arquivo de vídeo em uma pasta existente."""
    destino = destino.expanduser()

    if destino.suffix.lower() not in (".mp4", ".mkv", ".mov"):
        raise ErroLegendagem(
            f"A saída precisa terminar em .mp4, .mkv ou .mov (recebi '{destino.suffix}')."
        )

    if not destino.parent.is_dir():
        raise ErroLegendagem(f"A pasta de destino não existe: {destino.parent}")

    if isinstance(video, (str, Path)) and destino.resolve() == Path(video).resolve():
        raise ErroLegendagem(
            "A saída não pode ser o mesmo arquivo do vídeo de entrada. "
            "Escolha outro nome."
        )

    return destino.resolve()


# --------------------------------------------------------------------------- #
# Legenda
# --------------------------------------------------------------------------- #


def _preparar_legenda(texto: str, pasta: Path) -> Path:
    """Grava o SRT em disco, no formato que o ffmpeg espera."""
    if not texto or "-->" not in texto:
        raise ErroLegendagem("A legenda não parece um arquivo SRT válido.")

    arquivo = pasta / "legenda.srt"
    # utf-8 com BOM: o libass e o mp4 lidam bem, e players antigos também.
    arquivo.write_text(texto.strip() + "\n", encoding="utf-8-sig")
    return arquivo


# --------------------------------------------------------------------------- #
# ffmpeg
# --------------------------------------------------------------------------- #


def _percentual(linha: str, duracao: float | None) -> int | None:
    """Converte uma linha do `-progress` do ffmpeg em porcentagem."""
    if not duracao or not linha.startswith("out_time="):
        return None

    valor = linha.split("=", 1)[1].strip()
    if valor in ("", "N/A"):
        return None

    partes = valor.split(":")
    try:
        horas, minutos, segundos = (float(parte) for parte in partes)
    except ValueError:
        return None

    decorrido = horas * 3600 + minutos * 60 + segundos
    return max(0, min(99, int(decorrido / duracao * 100)))


def _comando_queimar(video: Path, legenda: Path, destino: Path) -> list[str]:
    # O filtro de legendas roda com o diretório de trabalho na pasta da legenda:
    # assim o nome passado ao filtro não tem ":" nem "\" para escapar.
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-progress",
        "pipe:1",
        "-y",
        "-i",
        str(video),
        "-vf",
        f"subtitles={legenda.name}",
        "-c:v",
        "libx264",
        "-preset",
        PRESET,
        "-crf",
        CRF,
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        BITRATE_AUDIO,
        "-movflags",
        "+faststart",
        str(destino),
    ]


def _comando_embutir(video: Path, legenda: Path, destino: Path) -> list[str]:
    codec = "srt" if destino.suffix.lower() == ".mkv" else "mov_text"
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-progress",
        "pipe:1",
        "-y",
        "-i",
        str(video),
        "-i",
        str(legenda),
        "-map",
        "0:v",
        "-map",
        "0:a?",
        "-map",
        "1:0",
        "-c",
        "copy",
        "-c:s",
        codec,
        "-metadata:s:s:0",
        "language=por",
        str(destino),
    ]


def _executar(
    comando: list[str],
    *,
    pasta: Path,
    duracao: float | None,
    progresso: Progresso | None,
) -> None:
    processo = subprocess.Popen(
        comando,
        cwd=str(pasta),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert processo.stdout is not None

    # O ffmpeg escreve o progresso várias vezes por segundo; sem o filtro, a
    # interface receberia dezenas de atualizações com a mesma porcentagem.
    ultimo: int | None = None
    for linha in processo.stdout:
        percentual = _percentual(linha, duracao)
        if percentual is None or progresso is None or percentual == ultimo:
            continue
        ultimo = percentual
        progresso(f"Colocando a legenda... {percentual}%")

    processo.wait()
    erro = (processo.stderr.read() if processo.stderr else "") or ""
    processo.stdout.close()
    if processo.stderr:
        processo.stderr.close()

    if processo.returncode != 0:
        detalhe = erro.strip().splitlines()[-1] if erro.strip() else "sem detalhe"
        raise ErroLegendagem(f"O ffmpeg falhou ao colocar a legenda. {detalhe}")


# --------------------------------------------------------------------------- #
# Fluxo completo
# --------------------------------------------------------------------------- #


def inserir_legenda(
    video: object,
    legenda: str,
    *,
    modo: str = MODO_QUEIMAR,
    destino: Path | None = None,
    progresso: Progresso | None = None,
) -> ResultadoInsercao:
    """Coloca a legenda no vídeo e devolve o caminho do arquivo gerado.

    `video` aceita um caminho (str/Path) ou um objeto file-like (UploadedFile).
    """
    if modo not in MODOS:
        raise ErroLegendagem(f"Modo desconhecido: {modo}. Use 'queimar' ou 'embutir'.")

    if not ffmpeg_disponivel():
        raise ErroLegendagem(
            "O ffmpeg não foi encontrado no PATH. Ele é necessário para colocar a "
            "legenda no vídeo (no Windows: winget install Gyan.FFmpeg)."
        )

    nome = nome_original(video)
    extensao = Path(nome).suffix.lower()
    saida = _validar_saida(
        Path(destino) if destino else destino_padrao(video, modo), video
    )

    inicio = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix="legendador_insercao_") as pasta_temporaria:
        pasta = Path(pasta_temporaria)

        if progresso is not None:
            progresso("Preparando o vídeo...")

        entrada = entrada_local(video, pasta, extensao)
        arquivo_legenda = _preparar_legenda(legenda, pasta)
        duracao = duracao_segundos(entrada)

        comando = (
            _comando_queimar(entrada, arquivo_legenda, saida)
            if modo == MODO_QUEIMAR
            else _comando_embutir(entrada, arquivo_legenda, saida)
        )

        if progresso is not None:
            progresso("Colocando a legenda...")

        try:
            _executar(comando, pasta=pasta, duracao=duracao, progresso=progresso)
        except ErroLegendagem:
            # Nada pior que um arquivo pela metade parecendo um vídeo pronto.
            saida.unlink(missing_ok=True)
            raise

    if not saida.is_file() or saida.stat().st_size == 0:
        raise ErroLegendagem("O ffmpeg não gerou o arquivo de saída.")

    return ResultadoInsercao(
        caminho=saida,
        modo=modo,
        duracao_segundos=duracao,
        tempo=time.perf_counter() - inicio,
        faixas_de_legenda=faixas_de_legenda(saida),
    )


# --------------------------------------------------------------------------- #
# Inspeção (usada para mostrar o resultado na interface)
# --------------------------------------------------------------------------- #


def _ffprobe(caminho: Path, *argumentos: str) -> str:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return ""

    resultado = subprocess.run(
        [ffprobe, "-v", "error", *argumentos, str(caminho)],
        capture_output=True,
        text=True,
    )
    return resultado.stdout if resultado.returncode == 0 else ""


def faixas_de_legenda(caminho: Path) -> tuple[str, ...]:
    """Idiomas das faixas de legenda do arquivo (vazio se não tiver nenhuma)."""
    saida = _ffprobe(
        caminho,
        "-select_streams",
        "s",
        "-show_entries",
        "stream_tags=language",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
    )
    return tuple(linha.strip() for linha in saida.splitlines() if linha.strip())


def extrair_quadro(
    video: Path, segundos: float, destino: Path, largura: int = 720
) -> Path:
    """Salva um quadro do vídeo — serve para conferir a legenda queimada."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise ErroLegendagem("O ffmpeg não foi encontrado no PATH.")

    resultado = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{max(0.0, segundos):.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-vf",
            f"scale={largura}:-2",
            str(destino),
        ],
        capture_output=True,
        text=True,
    )

    if resultado.returncode != 0 or not destino.is_file():
        raise ErroLegendagem("Não consegui extrair um quadro para a prévia.")

    return destino


def momento_de_amostra(duracao: float | None, blocos: int = 1) -> float:
    """Segundo do vídeo usado na prévia: um pouco depois do começo."""
    if not duracao or duracao <= 0:
        return 1.0
    return min(max(1.0, duracao * 0.05), duracao * 0.5)
