# Legendador de Vídeo e Áudio

Gera legendas **SRT** e **VTT** automaticamente a partir de vídeos e áudios, e
**coloca a legenda dentro do vídeo** — queimada na imagem ou como faixa
selecionável.

🔒 **100% local e gratuito.** A transcrição roda na sua própria máquina com o
Whisper — **nenhuma API paga, nenhuma chave, nenhum dado enviado para fora**.
Depois do primeiro download do modelo, o projeto funciona sem internet.

## Como funciona

A interface tem duas telas.

**1. Extrair legenda**

1. Você aponta um vídeo ou áudio (upload ou caminho no disco).
2. O áudio é extraído e convertido para **MP3 mono 16 kHz** com o ffmpeg
   (a taxa de amostragem nativa do Whisper).
3. O áudio é transcrito localmente pelo **Whisper**, via `faster-whisper`
   (CTranslate2). O modelo fica em cache de memória entre requisições.
4. Como o Whisper marca o tempo de cada palavra, as legendas são reformatadas
   no padrão profissional: **no máximo 42 caracteres por linha e 2 linhas por
   bloco**, com quebras preferencialmente em fronteiras naturais de frase.
5. A legenda aparece na tela e pode ser baixada como `.srt` ou `.vtt`.

> **Áudio cantado:** em música, o filtro de silêncio do Whisper descarta o canto
> junto com a música. Desmarque **Ignorar trechos sem fala** na barra lateral
> (ou use `--sem-vad` na linha de comando) — num teste com lyric video, isso
> passou de 7 para 143 blocos. Em compensação, fica mais lento e pode inventar
> texto em trechos realmente vazios.

**2. Inserir legenda no vídeo**

A legenda usada é a da extração (reaproveitada automaticamente) ou um `.srt`/
`.vtt` seu. O vídeo pode ser o mesmo de onde a legenda saiu, outro caminho no
disco ou um novo upload.

| Modo | O que faz | Quando usar |
| --- | --- | --- |
| **Queimar** (hardsub) | O texto vira pixel. Reencoda em H.264 + AAC. | Redes sociais, celular, qualquer player. |
| **Embutir** (softsub) | Adiciona uma faixa selecionável. **Não reencoda.** | Arquivo de trabalho, player que liga/desliga legenda. |

### Sincronia

Quando a legenda vem da tela de extração, os tempos são **os do próprio
arquivo**: o mesmo vídeo, a mesma linha do tempo, nenhum deslocamento. Não há
"sincronizar no olho" — o alinhamento é consequência de os dois arquivos
descreverem o mesmo tempo.

Depois de gerar, a tela mostra um **quadro do vídeo final** tirado de dentro do
primeiro bloco de legenda, para você confirmar o resultado na hora. Se a
legenda veio de outro vídeo, o app avisa que os tempos podem não bater.

## Requisitos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) para gerenciar o ambiente
- [ffmpeg](https://ffmpeg.org/) no `PATH` (extrair o áudio e aplicar a legenda).
  A build do ffmpeg precisa ter `libass` (para queimar) — as builds do
  [Gyan](https://www.gyan.dev/ffmpeg/builds/) têm.

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

# Música cantada: sem o filtro de silêncio
uv run legendador clipe.mp4 --sem-vad

# Baixar um modelo antecipadamente (deixa tudo pronto para uso offline)
uv run legendador --baixar-modelo small
uv run legendador --baixar-modelo todos
```

## Interface web

```bash
uv run streamlit run main.py
```

A aplicação fica disponível em <http://localhost:8501>, com a navegação entre as
duas telas na barra lateral.

`uv run main.py` e `python main.py` também funcionam: o `main.py` detecta que foi
executado fora do Streamlit e se reinicia pelo comando correto. Rodar o arquivo
e esperar que a tela apareça sozinha não funciona, porque o Streamlit precisa
subir o servidor — é justamente esse desvio que o `main.py` faz por você.

O resultado do modo **queimar** é salvo ao lado do vídeo original, com o sufixo
`_legendado` (`Churrasco.mp4` → `Churrasco_legendado.mp4`); o modo **embutir**
usa `_comlegenda`. O caminho é editável na tela e o arquivo original nunca é
alterado.

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
| `insercao.py` | Colocar a legenda no vídeo (queimar/embutir), progresso e inspeção do resultado. |
| `ui.py` | Peças de interface compartilhadas pelas duas telas (campos de arquivo, formatação). |
| `tela_extrair.py` | Tela 1: transcrição e download da legenda. |
| `tela_inserir.py` | Tela 2: aplicação da legenda no vídeo e conferência de sincronia. |
| `main.py` | Roteador das telas e ponto de entrada do Streamlit. |
| `cli.py` | Linha de comando (console script `legendador`), só para extração. |
| `.streamlit/config.toml` | Limite de upload (2 GB) e telemetria desligada. |
| `tests/` | Testes do núcleo, das legendas, da inserção e das telas. |

O núcleo expõe duas funções:

```python
from insercao import MODO_EMBUTIR, MODO_QUEIMAR, inserir_legenda
from legendador import legendar

resultado = legendar("Churrasco.mp4", idioma="pt", modelo="small")
print(resultado.srt)          # conteúdo da legenda
print(resultado.nome_saida)   # "Churrasco.srt"
print(resultado.velocidade)   # quantas vezes mais rápido que o tempo real

video = inserir_legenda("Churrasco.mp4", resultado.srt, modo=MODO_QUEIMAR)
print(video.caminho)          # Churrasco_legendado.mp4
print(video.tempo)            # segundos gastos
```

## Licença

Uso educacional. Sinta-se à vontade para estudar e modificar o código.
