"""
Núcleo do Legendador de Vídeo e Áudio.

Tudo roda localmente, sem nenhuma API paga:

1. O áudio é extraído do vídeo com o ffmpeg (gratuito e offline).
2. A transcrição é feita pelo Whisper rodando na sua máquina, via
   faster-whisper (CTranslate2). Os modelos são baixados uma vez do
   Hugging Face e depois funcionam sem internet.
3. As legendas são montadas a partir da marcação de tempo por palavra.

Este módulo não depende do Streamlit nem da linha de comando: pode ser usado
em scripts, notebooks ou como worker de fila.
"""

from __future__ import annotations

import contextlib
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from legendas import (
    Legenda,
    Palavra,
    legendas_de_segmentos,
    montar_legendas,
    para_srt,
    para_vtt,
)

MODELOS_DISPONIVEIS = ("tiny", "base", "small", "medium", "large-v3")
MODELO_PADRAO = "small"

# Áudio entregue ao Whisper: MP3 mono na taxa nativa do modelo (16 kHz).
FORMATO_AUDIO = "mp3"
BITRATE_AUDIO = "48k"
TAXA_AMOSTRAL = "16000"
CANAIS = "1"

# Tamanho do pedaço lido ao gravar um upload em disco (1 MB).
TAMANHO_BLOCO = 1024 * 1024

EXTENSOES_SUPORTADAS = (
    ".mp4",
    ".mp3",
    ".m4a",
    ".aac",
    ".wav",
    ".flac",
    ".ogg",
    ".oga",
    ".opus",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
)

# Callback opcional para reportar o andamento (usado pela CLI e pelo Streamlit).
Progresso = Callable[[str], None]


class ErroLegendagem(Exception):
    """Erro com mensagem já pronta para ser exibida ao usuário final."""


@dataclass(frozen=True)
class ResultadoLegenda:
    """Resultado de uma legendagem bem-sucedida."""

    srt: str
    nome_base: str
    modelo: str
    dispositivo: str
    idioma: str | None
    idioma_detectado: str | None
    probabilidade_idioma: float
    duracao_segundos: float | None
    tempo_transcricao: float
    legendas: list[Legenda] = field(default_factory=list)

    @property
    def nome_saida(self) -> str:
        """Nome do arquivo de legenda para download."""
        return f"{self.nome_base}.srt"

    @property
    def velocidade(self) -> float:
        """Quantas vezes mais rápido que o tempo real a transcrição rodou."""
        if not self.duracao_segundos or not self.tempo_transcricao:
            return 0.0
        return self.duracao_segundos / self.tempo_transcricao


# --------------------------------------------------------------------------- #
# Utilitários internos
# --------------------------------------------------------------------------- #


def notificar(progresso: Progresso | None, mensagem: str) -> None:
    if progresso is not None:
        progresso(mensagem)


def ffmpeg_disponivel() -> bool:
    """Indica se o ffmpeg (necessário para extrair o áudio) está no PATH."""
    return shutil.which("ffmpeg") is not None


def nome_original(arquivo: object) -> str:
    """Nome do arquivo de entrada, com extensão."""
    if isinstance(arquivo, (str, Path)):
        return Path(arquivo).name
    nome = getattr(arquivo, "name", None)
    return Path(nome).name if nome else "arquivo"


def entrada_local(arquivo: object, pasta: Path, extensao: str) -> Path:
    """Devolve um caminho de arquivo real para o ffmpeg ler.

    Um caminho (str/Path) é usado direto: copiar um vídeo de 2 GB para uma
    pasta temporária gastaria disco e tempo sem nenhum ganho. Um upload
    (UploadedFile do Streamlit) é gravado em pedaços, para não carregar o
    arquivo inteiro uma segunda vez na memória.
    """
    if isinstance(arquivo, (str, Path)):
        origem = Path(arquivo)
        if not origem.is_file():
            raise ErroLegendagem(f"Arquivo não encontrado: {origem}")
        return origem

    destino = pasta / f"entrada{extensao}"

    with contextlib.suppress(AttributeError, OSError, ValueError):
        arquivo.seek(0)  # type: ignore[attr-defined]

    tamanho = 0
    with destino.open("wb") as saida:
        while bloco := arquivo.read(TAMANHO_BLOCO):  # type: ignore[attr-defined]
            saida.write(bloco)
            tamanho += len(bloco)

    if not tamanho:
        raise ErroLegendagem("O arquivo enviado está vazio.")
    return destino


def duracao_segundos(caminho: Path) -> float | None:
    """Duração do arquivo em segundos (via ffprobe), ou None se não for possível."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None

    resultado = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(caminho),
        ],
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        return None
    try:
        return round(float(resultado.stdout.strip()), 1)
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# Extração de áudio
# --------------------------------------------------------------------------- #


def extrair_audio(arquivo: Path, destino: Path) -> Path:
    """Converte o arquivo de entrada em MP3 mono 16 kHz (taxa nativa do Whisper).

    Reduzir a taxa de amostragem e os canais deixa o arquivo ~3x menor e
    acelera a transcrição, sem perda perceptível de qualidade.
    """
    comando = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(arquivo),
        "-vn",  # descarta o vídeo
        "-ac",
        CANAIS,  # mono
        "-ar",
        TAXA_AMOSTRAL,  # 16 kHz
        "-b:a",
        BITRATE_AUDIO,
        "-c:a",
        "libmp3lame",
        str(destino),
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0:
        linhas = (resultado.stderr or "").strip().splitlines()
        detalhe = f" O ffmpeg retornou: {linhas[-1]}" if linhas else ""
        raise ErroLegendagem("Não consegui extrair o áudio do arquivo." + detalhe)
    return destino


# --------------------------------------------------------------------------- #
# Modelo Whisper local
# --------------------------------------------------------------------------- #

_modelos: dict[tuple[str, str, str], object] = {}


def _cuda_disponivel() -> bool:
    """Indica se há uma GPU NVIDIA utilizável pelo CTranslate2."""
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:  # noqa: BLE001 - a ausência de CUDA não é um erro
        return False


def dispositivo_padrao() -> str:
    """'cuda' quando houver GPU NVIDIA, 'cpu' caso contrário."""
    return "cuda" if _cuda_disponivel() else "cpu"


def _compute_type(dispositivo: str) -> str:
    """Precisão de cálculo: float16 na GPU (rápido), int8 na CPU (leve)."""
    return "float16" if dispositivo == "cuda" else "int8"


def _obter_modelo(nome: str, dispositivo: str, compute_type: str):
    """Carrega (e memoriza) o modelo Whisper.

    Recarregar o modelo a cada chamada custaria ~15 s; o cache o mantém na
    memória entre requisições.
    """
    chave = (nome, dispositivo, compute_type)
    if chave in _modelos:
        return _modelos[chave]

    from faster_whisper import WhisperModel

    try:
        modelo = WhisperModel(nome, device=dispositivo, compute_type=compute_type)
    except Exception as exc:  # noqa: BLE001 - erro de download ou de instalação
        raise ErroLegendagem(
            f"Não consegui carregar o modelo Whisper '{nome}'. Se for a primeira "
            f"vez, é preciso internet para baixá-lo. Detalhe: {exc}"
        ) from exc

    _modelos[chave] = modelo
    return modelo


def baixar_modelo(nome: str) -> None:
    """Baixa antecipadamente um modelo Whisper (deixa o app pronto para uso offline)."""
    if nome not in MODELOS_DISPONIVEIS:
        raise ErroLegendagem(
            f"Modelo '{nome}' desconhecido. Use um destes: {', '.join(MODELOS_DISPONIVEIS)}."
        )

    print(f"Baixando o modelo '{nome}' (isso acontece só na primeira vez)...")
    dispositivo = dispositivo_padrao()
    _obter_modelo(nome, dispositivo, _compute_type(dispositivo))
    print(f"Modelo '{nome}' pronto.")


# --------------------------------------------------------------------------- #
# Transcrição
# --------------------------------------------------------------------------- #


def transcrever(
    audio: Path,
    *,
    idioma: str | None = "pt",
    modelo: str = MODELO_PADRAO,
    dispositivo: str | None = None,
    duracao: float | None = None,
    vad: bool = True,
    progresso: Progresso | None = None,
) -> tuple[str, str | None, float, list[Legenda], float]:
    """Transcreve um áudio localmente.

    `vad` liga o filtro de silêncio: ele pula os trechos sem fala, o que acelera
    e evita alucinação em áudio vazio — mas também descarta canto e fala sobre
    música. Desligue quando o conteúdo for cantado.

    Devolve (srt, idioma detectado, confiança do idioma, legendas, tempo gasto).
    """
    dispositivo = dispositivo or dispositivo_padrao()

    notificar(progresso, f"Carregando o modelo Whisper '{modelo}'...")
    whisper = _obter_modelo(modelo, dispositivo, _compute_type(dispositivo))

    notificar(progresso, "Transcrevendo o áudio...")
    segmentos, info = whisper.transcribe(
        str(audio),
        language=idioma,
        word_timestamps=True,
        vad_filter=vad,
        vad_parameters={"min_silence_duration_ms": 500} if vad else None,
    )

    # A transcrição só acontece enquanto o gerador é consumido.
    inicio = time.perf_counter()
    coletados = []
    for segmento in segmentos:
        coletados.append(segmento)
        if progresso and duracao:
            percentual = min(99, int(segmento.end / duracao * 100))
            progresso(f"Transcrevendo... {percentual}%")
    decorrido = time.perf_counter() - inicio

    palavras: list[Palavra] = []
    for segmento in coletados:
        for palavra in getattr(segmento, "words", None) or []:
            texto = (palavra.word or "").strip()
            if texto:
                palavras.append(
                    Palavra(texto=texto, inicio=palavra.start, fim=palavra.end)
                )

    if palavras:
        legendas = montar_legendas(palavras)
    else:
        # Nenhuma marcação por palavra: usa os blocos brutos como plano B.
        legendas = legendas_de_segmentos([(s.start, s.end, s.text) for s in coletados])

    idioma_detectado = getattr(info, "language", None)
    probabilidade = float(getattr(info, "language_probability", 0.0) or 0.0)

    notificar(progresso, "Legenda pronta!")
    return para_srt(legendas), idioma_detectado, probabilidade, legendas, decorrido


# --------------------------------------------------------------------------- #
# Fluxo completo
# --------------------------------------------------------------------------- #


def legendar(
    arquivo: object,
    *,
    idioma: str | None = "pt",
    modelo: str = MODELO_PADRAO,
    dispositivo: str | None = None,
    formato: str = "srt",
    vad: bool = True,
    progresso: Progresso | None = None,
) -> ResultadoLegenda:
    """Gera a legenda de um arquivo de vídeo ou áudio.

    Aceita um caminho (str/Path) ou um objeto file-like (UploadedFile do Streamlit).
    """
    nome = nome_original(arquivo)
    extensao = Path(nome).suffix.lower()

    if extensao not in EXTENSOES_SUPORTADAS:
        aceitas = ", ".join(EXTENSOES_SUPORTADAS)
        raise ErroLegendagem(
            f"Formato '{extensao or 'sem extensão'}' não suportado. Use um destes: {aceitas}."
        )

    if not ffmpeg_disponivel():
        raise ErroLegendagem(
            "O ffmpeg não foi encontrado no PATH. Ele é necessário para extrair o áudio "
            "do vídeo (no Windows: winget install Gyan.FFmpeg)."
        )

    nome_base = Path(nome).stem or "legenda"
    dispositivo = dispositivo or dispositivo_padrao()

    with tempfile.TemporaryDirectory(prefix="legendador_") as pasta:
        base = Path(pasta)
        entrada = entrada_local(arquivo, base, extensao)
        audio = base / f"audio.{FORMATO_AUDIO}"

        notificar(progresso, "Extraindo o áudio (16 kHz mono)...")
        extrair_audio(entrada, audio)
        duracao = duracao_segundos(entrada)

        srt, detectado, probabilidade, legendas, decorrido = transcrever(
            audio,
            idioma=idioma,
            modelo=modelo,
            dispositivo=dispositivo,
            duracao=duracao,
            vad=vad,
            progresso=progresso,
        )

        if formato == "vtt":
            srt = para_vtt(legendas)

    return ResultadoLegenda(
        srt=srt,
        nome_base=nome_base,
        modelo=modelo,
        dispositivo=dispositivo,
        idioma=idioma,
        idioma_detectado=detectado,
        probabilidade_idioma=probabilidade,
        duracao_segundos=duracao,
        tempo_transcricao=decorrido,
        legendas=legendas,
    )


if __name__ == "__main__":
    # `python legendador.py ...` continua funcionando: delega para a CLI,
    # que é o lugar onde os argumentos são tratados.
    from cli import main as _main_cli

    raise SystemExit(_main_cli())
