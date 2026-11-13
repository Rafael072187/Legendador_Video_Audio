"""Fixtures compartilhadas pelos testes das duas telas."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

import legendador

RAIZ = Path(__file__).resolve().parent.parent
APP = RAIZ / "main.py"

# Tempos propositais: o bloco começa e termina dentro do vídeo de 3 s.
SRT_FALSO = "1\n00:00:00,500 --> 00:00:01,800\nOlá, isto é um teste.\n"


@pytest.fixture(scope="session")
def midia_teste(tmp_path_factory) -> Path:
    """Vídeo sintético de 3 segundos (tom + quadro preto), gerado com o ffmpeg."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg não está instalado")

    destino = tmp_path_factory.mktemp("midia") / "teste.mp4"
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
            "sine=frequency=440:duration=3",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x240:r=5:d=3",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(destino),
        ],
        check=True,
    )
    return destino


@pytest.fixture
def transcricao_mockada(monkeypatch):
    """Substitui a transcrição local por uma fixa e conta as chamadas."""
    chamadas: list[dict] = []

    def falsa_transcricao(
        audio,
        *,
        idioma=None,
        modelo=None,
        dispositivo=None,
        duracao=None,
        progresso=None,
    ):
        chamadas.append(
            {
                "audio": Path(audio),
                "idioma": idioma,
                "modelo": modelo,
                "dispositivo": dispositivo,
            }
        )
        return SRT_FALSO, "pt", 0.99, [], 1.0

    monkeypatch.setattr(legendador, "transcrever", falsa_transcricao)
    return chamadas
