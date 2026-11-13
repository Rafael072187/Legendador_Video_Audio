"""Testes da inserção de legenda no vídeo (queimar e embutir)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from insercao import (
    MODO_EMBUTIR,
    MODO_QUEIMAR,
    _percentual,
    destino_padrao,
    faixas_de_legenda,
    inserir_legenda,
)
from legendador import ErroLegendagem

# Bloco entre 1,0 s e 2,5 s: dá para medir antes, dentro e depois.
SRT = "1\n00:00:01,000 --> 00:00:02,500\nTeste de sincronia\n"

SEGUNDO_ANTES = 0.3
SEGUNDO_DENTRO = 1.7
SEGUNDO_DEPOIS = 3.5


@pytest.fixture(scope="module")
def video_liso(tmp_path_factory) -> Path:
    """Vídeo de 4 s com fundo cinza uniforme.

    O fundo liso é proposital: qualquer pixel mais claro só pode ser a legenda,
    o que torna a verificação de sincronia possível sem olhar o vídeo.
    """
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg não está instalado")

    destino = tmp_path_factory.mktemp("midia_insercao") / "fundo.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x303030:s=320x240:r=15:d=4",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=4",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(destino),
        ],
        check=True,
    )
    return destino


# --------------------------------------------------------------------------- #
# Utilidades dos testes
# --------------------------------------------------------------------------- #


def _pixels_claros(video: Path, segundos: float) -> int:
    """Quantos pixels são quase brancos num quadro.

    O fundo do vídeo de teste é cinza escuro (~48), então só o texto da legenda
    pode ser claro. Contar pixels é bem mais sensível que a média do quadro:
    numa tela pequena o texto ocupa pouca área.
    """
    bruto = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            f"{segundos:.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "gray",
            "-",
        ],
        capture_output=True,
        check=True,
    ).stdout
    return sum(1 for tom in bruto if tom > 160)


def _legenda_embutida(video: Path, destino: Path) -> str:
    """Extrai a faixa de legenda do vídeo de volta para SRT."""
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(video),
            "-map",
            "0:s:0",
            "-f",
            "srt",
            str(destino),
        ],
        check=True,
    )
    return destino.read_text(encoding="utf-8")


def _tipos_de_faixa(video: Path) -> str:
    return subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "csv=p=0",
            str(video),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


# --------------------------------------------------------------------------- #
# Destino
# --------------------------------------------------------------------------- #


def test_destino_padrao_fica_ao_lado_do_video(tmp_path):
    video = tmp_path / "Churrasco.mp4"
    assert destino_padrao(video) == tmp_path / "Churrasco_legendado.mp4"


def test_destino_padrao_muda_com_o_modo(tmp_path):
    video = tmp_path / "video.mkv"
    assert destino_padrao(video, MODO_QUEIMAR).name == "video_legendado.mp4"
    assert destino_padrao(video, MODO_EMBUTIR).name == "video_comlegenda.mp4"


def test_destino_padrao_de_upload_vai_para_downloads():
    class FalsoUpload:
        name = "enviado.mp4"

    assert destino_padrao(FalsoUpload()).name == "enviado_legendado.mp4"


def test_saida_com_extensao_invalida(video_liso, tmp_path):
    with pytest.raises(ErroLegendagem, match="mp4"):
        inserir_legenda(video_liso, SRT, destino=tmp_path / "saida.txt")


def test_saida_nao_pode_ser_o_proprio_video(video_liso):
    with pytest.raises(ErroLegendagem, match="mesmo arquivo"):
        inserir_legenda(video_liso, SRT, destino=video_liso)


# --------------------------------------------------------------------------- #
# Validação de entrada
# --------------------------------------------------------------------------- #


def test_legenda_invalida(video_liso, tmp_path):
    with pytest.raises(ErroLegendagem, match="SRT"):
        inserir_legenda(video_liso, "isto não é legenda", destino=tmp_path / "a.mp4")


def test_legenda_vazia(video_liso, tmp_path):
    with pytest.raises(ErroLegendagem, match="SRT"):
        inserir_legenda(video_liso, "", destino=tmp_path / "a.mp4")


def test_video_inexistente(tmp_path):
    with pytest.raises(ErroLegendagem, match="não encontrado"):
        inserir_legenda(
            tmp_path / "nao_existe.mp4", SRT, destino=tmp_path / "saida.mp4"
        )


def test_modo_desconhecido(video_liso, tmp_path):
    with pytest.raises(ErroLegendagem, match="Modo"):
        inserir_legenda(
            video_liso, SRT, modo="queimar2", destino=tmp_path / "saida.mp4"
        )


# --------------------------------------------------------------------------- #
# Queimar (hardsub) — a sincronia é medida em pixel
# --------------------------------------------------------------------------- #


def test_queimar_coloca_o_texto_no_tempo_certo(video_liso, tmp_path):
    """O texto tem de aparecer entre 1,0 s e 2,5 s — nem antes, nem depois."""
    destino = tmp_path / "queimado.mp4"
    resultado = inserir_legenda(video_liso, SRT, modo=MODO_QUEIMAR, destino=destino)

    assert resultado.caminho == destino.resolve()
    assert destino.stat().st_size > 0
    assert resultado.modo == MODO_QUEIMAR
    assert resultado.duracao_segundos == pytest.approx(4.0, abs=0.5)

    antes = _pixels_claros(destino, SEGUNDO_ANTES)
    dentro = _pixels_claros(destino, SEGUNDO_DENTRO)
    depois = _pixels_claros(destino, SEGUNDO_DEPOIS)

    assert antes == 0, f"nada deveria estar escrito em {SEGUNDO_ANTES}s"
    assert depois == 0, f"o texto não deveria continuar em {SEGUNDO_DEPOIS}s"
    assert dentro > 100, (
        "o quadro no meio do bloco deveria mostrar o texto branco "
        f"(pixels claros={dentro})"
    )


def test_queimar_remove_a_faixa_de_legenda(video_liso, tmp_path):
    """Queimada vira pixel: não sobra faixa selecionável no arquivo."""
    destino = tmp_path / "queimado.mp4"
    inserir_legenda(video_liso, SRT, modo=MODO_QUEIMAR, destino=destino)

    assert "subtitle" not in _tipos_de_faixa(destino)
    assert faixas_de_legenda(destino) == ()


def test_queimar_mantem_o_audio(video_liso, tmp_path):
    destino = tmp_path / "queimado.mp4"
    inserir_legenda(video_liso, SRT, modo=MODO_QUEIMAR, destino=destino)

    assert "audio" in _tipos_de_faixa(destino)


def test_queimar_informa_o_andamento(video_liso, tmp_path):
    mensagens: list[str] = []
    inserir_legenda(
        video_liso,
        SRT,
        modo=MODO_QUEIMAR,
        destino=tmp_path / "queimado.mp4",
        progresso=mensagens.append,
    )

    assert any("legenda" in mensagem.lower() for mensagem in mensagens)


# --------------------------------------------------------------------------- #
# Embutir (softsub) — a sincronia é medida nos timestamps
# --------------------------------------------------------------------------- #


def test_embutir_preserva_os_tempos_da_legenda(video_liso, tmp_path):
    """A faixa embutida tem exatamente os tempos do SRT de origem."""
    destino = tmp_path / "embutido.mp4"
    resultado = inserir_legenda(video_liso, SRT, modo=MODO_EMBUTIR, destino=destino)

    assert resultado.faixas_de_legenda == ("por",)

    extraida = _legenda_embutida(destino, tmp_path / "extraida.srt")
    assert "00:00:01,000 --> 00:00:02,500" in extraida
    assert "Teste de sincronia" in extraida


def test_embutir_nao_reencoda_o_video(video_liso, tmp_path):
    """Sem reencode, o vídeo continua idêntico (cópia de fluxo)."""
    destino = tmp_path / "embutido.mp4"
    inserir_legenda(video_liso, SRT, modo=MODO_EMBUTIR, destino=destino)

    def checksum(caminho: Path) -> str:
        return subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                str(caminho),
                "-map",
                "0:v",
                "-c",
                "copy",
                "-f",
                "md5",
                "-",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    assert checksum(destino) == checksum(video_liso)


def test_embutir_aceita_saida_mkv(video_liso, tmp_path):
    destino = tmp_path / "embutido.mkv"
    resultado = inserir_legenda(video_liso, SRT, modo=MODO_EMBUTIR, destino=destino)

    assert resultado.caminho.suffix == ".mkv"
    assert faixas_de_legenda(destino) == ("por",)


# --------------------------------------------------------------------------- #
# Progresso
# --------------------------------------------------------------------------- #


def test_percentual_a_partir_da_saida_do_ffmpeg():
    assert _percentual("out_time=00:00:02.500000\n", 5.0) == 50
    assert _percentual("out_time=00:00:00.000000\n", 5.0) == 0
    assert _percentual("out_time=N/A\n", 5.0) is None
    assert _percentual("frame=10\n", 5.0) is None
    assert _percentual("out_time=00:00:05.000000\n", 5.0) == 99  # nunca 100
    assert _percentual("out_time=00:00:05.000000\n", None) is None
