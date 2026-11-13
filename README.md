# Legendador de Vídeo e Áudio

Gera legendas **SRT** e **VTT** automaticamente a partir de vídeos e áudios.

🔒 **100% local e gratuito.** A transcrição roda na sua própria máquina com o
Whisper — **nenhuma API paga, nenhuma chave, nenhum dado enviado para fora**.
Depois do primeiro download do modelo, o projeto funciona sem internet.

## Como funciona

1. Você envia um vídeo ou áudio pela interface (ou pela linha de comando).
2. O áudio é extraído e convertido para **MP3 mono 16 kHz** com o ffmpeg
   (a taxa de amostragem nativa do Whisper).
3. O áudio é transcrito localmente pelo **Whisper**, via `faster-whisper`
   (CTranslate2). O modelo fica em cache de memória entre requisições.
4. Como o Whisper marca o tempo de cada palavra, as legendas são reformatadas
   no padrão profissional: **no máximo 42 caracteres por linha e 2 linhas por
   bloco**, com quebras preferencialmente em fronteiras naturais de frase.
5. A legenda aparece na tela e pode ser baixada como `.srt` ou `.vtt`.

## Requisitos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) para gerenciar o ambiente
- [ffmpeg](https://ffmpeg.org/) no `PATH` (necessário para extrair o áudio)

### Instalando o ffmpeg (Windows)

```powershell
winget install Gyan.FFmpeg
```

Reinicie o terminal depois de instalar para que o comando passe a ser reconhecido.

## Instalação

```bash
git clone https://github.com/Rafael072187/Legendador_Video_Audio.git
cd Legendador_Video_Audio
uv sync
```

Não é preciso criar `.env` nem configurar chave de API: **não existe dependência
de serviço pago neste projeto**.

Todos os comandos abaixo usam `uv run`, que executa dentro do ambiente do
projeto sem precisar ativar o `.venv`.

## Linha de comando

```bash
# Legendar um vídeo
uv run legendador Churrasco.mp4

# Escolher modelo, idioma e formato de saída
uv run legendador audio.mp3 --modelo medium --idioma en --formato vtt

# Baixar um modelo antecipadamente (deixa tudo pronto para uso offline)
uv run legendador --baixar-modelo small
uv run legendador --baixar-modelo todos
```

## Interface web

```bash
uv run streamlit run main.py
```

A aplicação fica disponível em <http://localhost:8501>.

`uv run main.py` e `python main.py` também funcionam: o `main.py` detecta que foi
executado fora do Streamlit e se reinicia pelo comando correto. Rodar o arquivo
e esperar que a tela apareça sozinha não funciona, porque o Streamlit precisa
subir o servidor — é justamente esse desvio que o `main.py` faz por você.

## Arquivos grandes

A interface oferece duas origens:

| Modo | Limite | Como funciona |
| --- | --- | --- |
| **Upload** | 2 GB | O arquivo passa pelo navegador e fica na memória do servidor. |
| **Caminho no disco** | **nenhum** | O ffmpeg lê o arquivo direto do seu disco; nada é enviado, nada é copiado. |

O limite de upload não é escolha do projeto: `200 MB` é o padrão do Streamlit.
Ele está elevado para 2 GB em [`.streamlit/config.toml`](.streamlit/config.toml).
Para arquivos maiores — ou simplesmente para não esperar o upload de um vídeo
que já está no seu computador — use **Caminho no disco**: é instantâneo e não
duplica o arquivo em memória nem em disco.

O modo caminho também é mais rápido na prática: não há cópia para pasta
temporária. Só o áudio extraído (MP3 mono 16 kHz) é gravado, e ele é descartado
no final.

> Rode o Streamlit a partir da raiz do projeto para que a
> `.streamlit/config.toml` seja lida: `uv run streamlit run main.py`.

## Modelos Whisper

O modelo é baixado do Hugging Face na primeira vez e fica em cache
(`~/.cache/huggingface`). Medições nesta máquina
(AMD Ryzen 5 5600G, 6 núcleos, **sem GPU**, `int8`):

| Modelo | Download | Velocidade | Quando usar |
| --- | --- | --- | --- |
| `tiny` | 75 MB | ~30x tempo real | Testes, áudio limpo e fácil |
| `base` | 145 MB | ~11x tempo real | Qualidade básica |
| `small` | 484 MB | ~4x tempo real | **Recomendado** — equilíbrio ideal |
| `medium` | 1,5 GB | ~1,2x tempo real | Qualidade alta, áudio difícil |
| `large-v3` | 3 GB | ~0,5x tempo real | Qualidade máxima, bem mais lento |

O `small` entrega resultado equivalente ao `whisper-1` da OpenAI no teste de
referência, sem custo por minuto.

Com GPU NVIDIA (CUDA) o projeto detecta automaticamente e usa `float16`, o que
multiplica a velocidade. Em CPU ele usa `int8`.

## Testes

```bash
uv run pytest
```

## Estrutura

| Arquivo | Responsabilidade |
| --- | --- |
| `legendador.py` | Núcleo: extração de áudio, transcrição local e resultado. |
| `legendas.py` | Montagem das legendas: agrupamento por palavra, quebra de linhas e saída SRT/VTT. |
| `cli.py` | Linha de comando (console script `legendador`). |
| `main.py` | Interface web (Streamlit). |
| `.streamlit/config.toml` | Limite de upload (2 GB) e telemetria desligada. |
| `tests/` | Testes do núcleo, das legendas e da interface. |

O núcleo expõe uma única função:

```python
from legendador import legendar

resultado = legendar("Churrasco.mp4", idioma="pt", modelo="small")
print(resultado.srt)          # conteúdo da legenda
print(resultado.nome_saida)   # "Churrasco.srt"
print(resultado.velocidade)   # quantas vezes mais rápido que o tempo real
```

## Licença

Uso educacional. Sinta-se à vontade para estudar e modificar o código.
