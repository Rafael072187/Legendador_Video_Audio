from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

cliente = OpenAI()

""" 
Aqui estou abrindo o arquivo em modo de leitura no formanto de bits(rb=Leitura Binária), já que para a transcrição tem que passar o áudio no formato de bit
que são vários caracteres, no qual o modelo vai entender e transcreve o conteúdo do áudio.
"""
with open("Churrasco.mp3", "rb") as arquivo:
    transcricao = cliente.audio.transcriptions.create(
        model="whisper-1", # Modelo mais barato atualmente
        file=arquivo,
        language="pt", # Aqui ao passar o idioma usado, ele não tera quer idetificar o idioma facilitando o trabalho
        response_format="srt" # O formato srt(SubRip Subtitle) é o formanto padrão de criação de legendas e mais comum de ser usado
        )

print(transcricao)

""" 
Aqui estou criando o arquivo da legenda abrindo e escrevendo(w) o texto, usando o encoding(utf-8) por conta dos caracteres especiais do idioma pt.
"""
with open("legenda.srt", "w", encoding="utf-8") as arquivo_legenda:
    arquivo_legenda.write(transcricao)