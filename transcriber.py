import os
import sys
import speech_recognition as sr
from pydub import AudioSegment
from pydub.silence import split_on_silence
import time

def transcribe_audio(input_file, output_dir, callback_progress=None, callback_error=None, callback_info=None):
    r = sr.Recognizer()
    
    # Configurações melhoradas para o reconhecedor
    r.energy_threshold = 300
    r.dynamic_energy_threshold = True
    r.pause_threshold = 0.8
    r.operation_timeout = None
    r.phrase_threshold = 0.3
    r.non_speaking_duration = 0.8
    
    # Carregar áudio e dividir com parâmetros melhorados
    sound = AudioSegment.from_wav(input_file)
    
    # Normalizar o áudio para melhor reconhecimento
    sound = sound.normalize()
    
    # Parâmetros melhorados para divisão
    chunks = split_on_silence(sound,
        min_silence_len=1000,  # Aumentado para evitar cortes muito frequentes
        silence_thresh=sound.dBFS-16,  # Threshold mais conservador
        keep_silence=800)  # Manter mais silêncio para contexto
    
    if callback_progress:
        callback_progress(f"Áudio dividido em {len(chunks)} segmentos")
    
    # Processar cada chunk com gerador
    for i, chunk in enumerate(chunks):
        # Pular chunks muito pequenos (menos de 1 segundo)
        if len(chunk) < 1000:
            if callback_progress:
                callback_progress(f"Chunk {i+1}/{len(chunks)} muito pequeno, pulando...")
            continue
            
        chunk_file = f"temp_chunk_{i}.wav"
        
        try:
            # Melhorar qualidade do chunk antes da transcrição
            chunk = chunk.set_frame_rate(16000)  # Taxa padrão para reconhecimento
            chunk = chunk.set_channels(1)  # Mono para melhor performance
            chunk.export(chunk_file, format="wav")
            
            with sr.AudioFile(chunk_file) as source:
                # Ajustar para ruído ambiente
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio_data = r.record(source)
                
                # Tentar múltiplos serviços se um falhar
                text = None
                
                # Primeiro: Google (mais preciso para português)
                try:
                    text = r.recognize_google(audio_data, language="pt-BR")
                except sr.UnknownValueError:
                    text = "[Áudio inaudível]"
                except sr.RequestError as e:
                    # Se Google falhar, tentar Sphinx offline
                    try:
                        text = r.recognize_sphinx(audio_data, language="pt-BR")
                    except:
                        text = f"[Erro de conexão: {str(e)}]"
                except Exception as e:
                    text = f"[Erro no reconhecimento: {str(e)}]"
                
            if callback_progress:
                callback_progress(f"Chunk {i+1}/{len(chunks)} transcrito: {text[:50]}...")
            
            yield text
            
            # Pequena pausa para evitar rate limiting
            time.sleep(0.1)
            
        except Exception as e:
            error_msg = f"[ERRO NO CHUNK {i}: {str(e)}]"
            if callback_error:
                callback_error(error_msg)
            if callback_progress:
                callback_progress(f"Erro no chunk {i+1}: {str(e)}")
            yield error_msg
        
        finally:
            # Limpar arquivo temporário
            try:
                if os.path.exists(chunk_file):
                    os.remove(chunk_file)
            except:
                pass

def converter_para_wav(arquivo_entrada):
    nome_base = os.path.splitext(arquivo_entrada)[0]
    saida_wav = nome_base + "_converted.wav"
    
    try:
        if arquivo_entrada.lower().endswith('.mp4'):
            audio = AudioSegment.from_file(arquivo_entrada, "mp4")
        elif arquivo_entrada.lower().endswith('.mp3'):
            audio = AudioSegment.from_mp3(arquivo_entrada)
        elif arquivo_entrada.lower().endswith('.wav'):
            return arquivo_entrada  # Já está em WAV
        else:
            raise ValueError(f"Formato não suportado: {arquivo_entrada}")
        
        # Configurações otimizadas para transcrição
        audio = audio.set_frame_rate(16000)
        audio = audio.set_channels(1)
        audio = audio.normalize()
        
        audio.export(saida_wav, format="wav")
        return saida_wav
        
    except Exception as e:
        raise Exception(f"Erro na conversão: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python transcriber.py <caminho_do_arquivo>")
        sys.exit(1)
    
    entrada = sys.argv[1]
    wav_file = converter_para_wav(entrada)
    
    resultado = ""
    for chunk in transcribe_audio(wav_file, "."):
        resultado += chunk + " "
    
    nome_saida = os.path.splitext(entrada)[0] + "_transcrito.txt"
    with open(nome_saida, "w", encoding="utf-8") as f:
        f.write(resultado)
    
    print(f"Transcrição concluída! Arquivo salvo em: {nome_saida}")