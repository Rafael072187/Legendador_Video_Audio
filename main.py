from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

cliente = OpenAI()

""" 
Aqui estou abrindo o arquivo em modo de leitura no formanto de bits, já que para a transcrição tem que passar o áudio no formato de bit
quer são vários caractere, no qual o modelo vai entender e transcreve o conteúdo do áudio.
"""
with open("Churrasco.mp3", "rb") as arquivo:
    transcricao = cliente.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe", # Modelo mais barato atualmente
        file=arquivo,
        language="pt" # Aqui ao passar o idioma usado, ele não tera quer idetificar o idioma facilitando o trabalho
        )

print(transcricao)