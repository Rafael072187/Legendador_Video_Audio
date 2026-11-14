"""Linha de comando do Legendador de Vídeo e Áudio."""

from __future__ import annotations

import argparse
from pathlib import Path

from legendador import (
    MODELO_PADRAO,
    MODELOS_DISPONIVEIS,
    ErroLegendagem,
    baixar_modelo,
    legendar,
)


def _criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="legendador",
        description="Gera legendas SRT/VTT localmente, sem nenhuma API paga.",
    )
    parser.add_argument("arquivo", nargs="?", help="vídeo ou áudio para legendar")
    parser.add_argument(
        "--modelo",
        default=MODELO_PADRAO,
        choices=MODELOS_DISPONIVEIS,
        help="tamanho do modelo Whisper (padrão: %(default)s)",
    )
    parser.add_argument(
        "--idioma",
        default="pt",
        help="código do idioma, ex.: pt, en (padrão: %(default)s) ou 'auto' para detectar",
    )
    parser.add_argument(
        "--formato",
        default="srt",
        choices=("srt", "vtt"),
        help="formato da legenda (padrão: %(default)s)",
    )
    parser.add_argument(
        "--dispositivo",
        default=None,
        choices=("cpu", "cuda"),
        help="força CPU ou GPU; por padrão detecta sozinho",
    )
    parser.add_argument("--saida", default=None, help="caminho do arquivo gerado")
    parser.add_argument(
        "--sem-vad",
        action="store_true",
        help="não ignora silêncios (use em música cantada ou fala sobre música)",
    )
    parser.add_argument(
        "--baixar-modelo",
        metavar="NOME",
        help="baixa um modelo Whisper e sai (use 'todos' para todos)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Executa a linha de comando e devolve o código de saída."""
    parser = _criar_parser()
    args = parser.parse_args(argv)

    try:
        if args.baixar_modelo:
            nomes = (
                MODELOS_DISPONIVEIS
                if args.baixar_modelo == "todos"
                else (args.baixar_modelo,)
            )
            for nome in nomes:
                baixar_modelo(nome)
            return 0

        if not args.arquivo:
            parser.print_help()
            return 1

        idioma = None if args.idioma.lower() in ("auto", "") else args.idioma
        resultado = legendar(
            args.arquivo,
            idioma=idioma,
            modelo=args.modelo,
            dispositivo=args.dispositivo,
            formato=args.formato,
            vad=not args.sem_vad,
            progresso=lambda mensagem: print(f"  {mensagem}"),
        )
    except ErroLegendagem as exc:
        print(f"Erro: {exc}")
        return 1

    destino = Path(args.saida) if args.saida else Path(resultado.nome_saida)
    destino.write_text(resultado.srt, encoding="utf-8")

    print()
    print(f"Legenda salva em: {destino.resolve()}")
    print(f"Blocos: {len(resultado.legendas)}")
    if resultado.idioma_detectado:
        print(
            f"Idioma: {resultado.idioma_detectado} ({resultado.probabilidade_idioma:.0%})"
        )
    if resultado.duracao_segundos:
        print(
            f"Tempo: {resultado.tempo_transcricao:.1f}s para "
            f"{resultado.duracao_segundos:.1f}s de áudio "
            f"({resultado.velocidade:.1f}x tempo real)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
