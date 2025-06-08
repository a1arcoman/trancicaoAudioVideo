import os
import sys
import speech_recognition as sr
from pydub import AudioSegment
from pydub.silence import split_on_silence
import time
import tempfile
import shutil

def format_timestamp(milliseconds):
    """Converte millisegundos para formato MM:SS"""
    total_seconds = int(milliseconds / 1000)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def transcribe_audio(input_file, output_dir, callback_progress=None, callback_error=None, callback_info=None, config=None):
    # Usar configurações padrão se não fornecidas
    if config is None:
        config = {
            'energy_threshold': 300,
            'pause_threshold': 0.6,
            'operation_timeout': 30,
            'phrase_threshold': 0.3,
            'non_speaking_duration': 0.6,
            'min_silence_len': 700,
            'silence_thresh_offset': -12,
            'keep_silence': 400,
            'chunk_length': 10000,
            'max_chunk_size': 15000,
            'sub_chunk_length': 8000,
            'max_tentativas': 2,
            'timeout_tentativa': 15,
            'pausa_entre_tentativas': 0.8,
            'sample_rate': 16000,
            'filtro_freq_baixa': 80,
            'filtro_freq_alta': 8000,
            'incluir_timestamp': False
        }
    
    r = sr.Recognizer()
    
    # Aplicar configurações do reconhecedor
    r.energy_threshold = config['energy_threshold']
    r.dynamic_energy_threshold = True
    r.pause_threshold = config['pause_threshold']
    r.operation_timeout = config['operation_timeout']
    r.phrase_threshold = config['phrase_threshold']
    r.non_speaking_duration = config['non_speaking_duration']
    
    # Criar pasta temporária
    temp_dir = tempfile.mkdtemp(prefix="transcricao_")
    
    try:
        # Carregar áudio e dividir com parâmetros configuráveis
        sound = AudioSegment.from_wav(input_file)
        
        # Normalizar o áudio para melhor reconhecimento
        sound = sound.normalize()
        
        # Usar configurações personalizadas para divisão
        chunks = split_on_silence(sound,
            min_silence_len=config['min_silence_len'],
            silence_thresh=sound.dBFS + config['silence_thresh_offset'],
            keep_silence=config['keep_silence'])
        
        # Calcular posições dos chunks para timestamps
        chunk_positions = []
        if config.get('incluir_timestamp', False):
            current_pos = 0
            if len(chunks) > 0:
                # Recalcular posições baseado nos chunks reais
                temp_sound = AudioSegment.empty()
                for i, chunk in enumerate(chunks):
                    chunk_positions.append(len(temp_sound))
                    temp_sound += chunk
                    if i < len(chunks) - 1:  # Adicionar silêncio entre chunks (exceto no último)
                        temp_sound += AudioSegment.silent(duration=config['keep_silence'])
        
        # Se não conseguir dividir bem, forçar divisão por tempo
        if len(chunks) == 0 or (len(chunks) == 1 and len(chunks[0]) > config['chunk_length'] * 3):
            if callback_progress:
                callback_progress("Áudio sem pausas detectadas, dividindo por tempo...")
            # Usar tamanho configurável para chunks
            chunk_length = config['chunk_length']
            chunks = []
            chunk_positions = []
            for i in range(0, len(sound), chunk_length):
                chunk = sound[i:i + chunk_length]
                if len(chunk) > 1000:  # Só adicionar se tiver pelo menos 1 segundo
                    chunks.append(chunk)
                    if config.get('incluir_timestamp', False):
                        chunk_positions.append(i)
        
        if callback_progress:
            callback_progress(f"Áudio dividido em {len(chunks)} segmentos")
        
        # Contador de sucessos para relatório
        chunks_processados = 0
        chunks_com_sucesso = 0
        
        # Processar cada chunk com gerador
        for i, chunk in enumerate(chunks):
            # Pular chunks muito pequenos (menos de 1 segundo)
            if len(chunk) < 1000:
                if callback_progress:
                    callback_progress(f"Chunk {i+1}/{len(chunks)} muito pequeno ({len(chunk)}ms), pulando...")
                continue
            
            # Calcular timestamp do chunk atual
            timestamp = None
            if config.get('incluir_timestamp', False) and i < len(chunk_positions):
                timestamp = format_timestamp(chunk_positions[i])
            
            # Se chunk for muito grande, dividir novamente
            if len(chunk) > config['max_chunk_size']:
                if callback_progress:
                    callback_progress(f"Chunk {i+1} muito grande ({len(chunk)}ms), subdividindo...")
                
                # Subdividir usando tamanho configurável
                sub_chunk_length = config['sub_chunk_length']
                sub_chunks = []
                for j in range(0, len(chunk), sub_chunk_length):
                    sub_chunk = chunk[j:j + sub_chunk_length]
                    if len(sub_chunk) > 1000:
                        sub_chunks.append(sub_chunk)
                
                # Processar sub-chunks
                for k, sub_chunk in enumerate(sub_chunks):
                    # Calcular timestamp do sub-chunk
                    sub_timestamp = None
                    if timestamp and config.get('incluir_timestamp', False):
                        sub_offset = k * sub_chunk_length
                        sub_timestamp = format_timestamp(chunk_positions[i] + sub_offset)
                    
                    result = process_single_chunk(sub_chunk, f"{i}_{k}", temp_dir, r, 
                                                 callback_progress, i+1, len(chunks), 
                                                 f"sub-chunk {k+1}/{len(sub_chunks)}", config, sub_timestamp)
                    if result:
                        chunks_processados += 1
                        texto = result.get('texto', str(result)) if isinstance(result, dict) else str(result)
                        if not texto.startswith("["):
                            chunks_com_sucesso += 1
                        yield result
            else:
                # Processar chunk normal
                result = process_single_chunk(chunk, str(i), temp_dir, r, 
                                             callback_progress, i+1, len(chunks), "", config, timestamp)
                if result:
                    chunks_processados += 1
                    texto = result.get('texto', str(result)) if isinstance(result, dict) else str(result)
                    if not texto.startswith("["):
                        chunks_com_sucesso += 1
                    yield result
        
        # Relatório final
        if callback_progress:
            callback_progress(f"\n=== RELATÓRIO DE TRANSCRIÇÃO ===")
            callback_progress(f"Chunks processados: {chunks_processados}")
            callback_progress(f"Chunks com sucesso: {chunks_com_sucesso}")
            callback_progress(f"Taxa de sucesso: {(chunks_com_sucesso/max(chunks_processados,1)*100):.1f}%")
    
    finally:
        # Limpar pasta temporária
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                if callback_progress:
                    callback_progress(f"Pasta temporária removida: {temp_dir}")
        except Exception as e:
            if callback_progress:
                callback_progress(f"Aviso: Não foi possível remover pasta temporária: {str(e)}")

def process_single_chunk(chunk, chunk_id, temp_dir, recognizer, callback_progress, chunk_num, total_chunks, extra_info="", config=None, timestamp=None):
    """Processa um único chunk de áudio e retorna o texto transcrito com timestamp opcional"""
    if config is None:
        config = {'sample_rate': 16000, 'filtro_freq_baixa': 80, 'filtro_freq_alta': 8000, 
                 'max_tentativas': 2, 'timeout_tentativa': 15, 'pausa_entre_tentativas': 0.8,
                 'incluir_timestamp': False}
    
    chunk_file = os.path.join(temp_dir, f"temp_chunk_{chunk_id}.wav")
    
    try:
        # Melhorar qualidade do chunk antes da transcrição
        chunk = chunk.set_frame_rate(config['sample_rate'])
        chunk = chunk.set_channels(1)  # Mono para melhor performance
        
        # Aplicar filtros para melhorar qualidade
        chunk = chunk.normalize()
        
        # Aplicar filtros de frequência se o chunk for longo o suficiente
        if len(chunk) > 2000:
            try:
                chunk = chunk.high_pass_filter(config['filtro_freq_baixa'])
                chunk = chunk.low_pass_filter(config['filtro_freq_alta'])
            except:
                pass  # Se filtros falharem, continuar sem eles
        
        chunk.export(chunk_file, format="wav")
        
        with sr.AudioFile(chunk_file) as source:
            # Ajustar para ruído ambiente com timeout menor
            try:
                recognizer.adjust_for_ambient_noise(source, duration=0.3)
            except:
                pass  # Se falhar, continuar sem ajuste
            
            audio_data = recognizer.record(source)
            
            # Tentar múltiplos serviços com timeouts progressivos
            text = None
            
            # Usar número configurável de tentativas
            for tentativa in range(config['max_tentativas']):
                try:
                    if callback_progress and tentativa > 0:
                        info_extra = f" {extra_info}" if extra_info else ""
                        callback_progress(f"  → Tentativa {tentativa + 1} para chunk {chunk_num}/{total_chunks}{info_extra}")
                    
                    # Usar timeout configurável
                    old_timeout = recognizer.operation_timeout
                    recognizer.operation_timeout = config['timeout_tentativa']
                    
                    text = recognizer.recognize_google(audio_data, language="pt-BR")
                    
                    recognizer.operation_timeout = old_timeout
                    break  # Sucesso, sair do loop
                    
                except sr.UnknownValueError:
                    text = "[Áudio inaudível]"
                    break
                    
                except sr.RequestError as e:
                    recognizer.operation_timeout = old_timeout
                    if "Bad Request" in str(e) or "quota" in str(e).lower():
                        if callback_progress:
                            callback_progress(f"  → Rate limit atingido, aguardando...")
                        time.sleep(3 + tentativa * 2)
                        continue
                    else:
                        # Erro diferente, tentar Sphinx imediatamente
                        try:
                            if callback_progress:
                                callback_progress(f"  → Tentando reconhecimento offline...")
                            text = recognizer.recognize_sphinx(audio_data, language="pt-BR")
                            break
                        except Exception as sphinx_error:
                            text = f"[Erro de conexão: {str(e)}]"
                            break
                            
                except Exception as e:
                    recognizer.operation_timeout = old_timeout
                    if "timed out" in str(e).lower():
                        if tentativa == config['max_tentativas'] - 1:  # Última tentativa
                            # Tentar Sphinx como último recurso
                            try:
                                if callback_progress:
                                    callback_progress(f"  → Timeout no Google, tentando Sphinx...")
                                text = recognizer.recognize_sphinx(audio_data, language="pt-BR")
                                break
                            except:
                                text = f"[Timeout após múltiplas tentativas]"
                        else:
                            time.sleep(1)
                    else:
                        if tentativa == config['max_tentativas'] - 1:
                            text = f"[Erro no reconhecimento: {str(e)}]"
                        else:
                            time.sleep(1)
            
            # Se ainda não temos texto após todas as tentativas
            if text is None:
                text = "[Falha na transcrição após múltiplas tentativas]"
        
        if callback_progress:
            preview = text[:50] + "..." if len(text) > 50 else text
            info_extra = f" {extra_info}" if extra_info else ""
            timestamp_info = f" [{timestamp}]" if timestamp else ""
            callback_progress(f"Chunk {chunk_num}/{total_chunks}{info_extra}{timestamp_info} transcrito: {preview}")
        
        # Usar pausa configurável
        time.sleep(config['pausa_entre_tentativas'])
        
        # Retornar resultado com ou sem timestamp
        if config.get('incluir_timestamp', False) and timestamp:
            return {
                'texto': text,
                'timestamp': timestamp
            }
        else:
            return text
        
    except Exception as e:
        error_msg = f"[ERRO NO CHUNK {chunk_id}: {str(e)}]"
        if callback_progress:
            callback_progress(f"Erro no chunk {chunk_num}: {str(e)}")
        
        if config.get('incluir_timestamp', False) and timestamp:
            return {
                'texto': error_msg,
                'timestamp': timestamp
            }
        else:
            return error_msg
    
    finally:
        # Limpar arquivo temporário do chunk
        try:
            if os.path.exists(chunk_file):
                os.remove(chunk_file)
        except:
            pass

def converter_para_wav(arquivo_entrada, config=None):
    if config is None:
        config = {'sample_rate': 16000, 'filtro_freq_baixa': 80, 'filtro_freq_alta': 8000}
    
    # Criar pasta temporária para conversão
    temp_dir = tempfile.mkdtemp(prefix="conversao_")
    nome_base = os.path.splitext(os.path.basename(arquivo_entrada))[0]
    saida_wav = os.path.join(temp_dir, nome_base + "_converted.wav")
    
    try:
        # Detectar formato e carregar
        if arquivo_entrada.lower().endswith('.mp4'):
            audio = AudioSegment.from_file(arquivo_entrada, "mp4")
        elif arquivo_entrada.lower().endswith('.mp3'):
            audio = AudioSegment.from_mp3(arquivo_entrada)
        elif arquivo_entrada.lower().endswith('.wav'):
            # Mesmo para WAV, vamos normalizar
            audio = AudioSegment.from_wav(arquivo_entrada)
        else:
            raise ValueError(f"Formato não suportado: {arquivo_entrada}")
        
        # Usar configurações personalizadas
        audio = audio.set_frame_rate(config['sample_rate'])
        audio = audio.set_channels(1)
        audio = audio.normalize()
        
        # Aplicar filtros configuráveis
        try:
            audio = audio.high_pass_filter(config['filtro_freq_baixa'])
            audio = audio.low_pass_filter(config['filtro_freq_alta'])
        except:
            pass  # Se filtros falharem, continuar sem eles
        
        audio.export(saida_wav, format="wav")
        return saida_wav
        
    except Exception as e:
        # Limpar em caso de erro
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except:
            pass
        raise Exception(f"Erro na conversão: {str(e)}")

# Função para limpar arquivos temporários de conversão
def limpar_arquivo_temp(arquivo_temp):
    try:
        if arquivo_temp and os.path.exists(arquivo_temp):
            temp_dir = os.path.dirname(arquivo_temp)
            if "conversao_" in temp_dir:
                shutil.rmtree(temp_dir)
    except:
        pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python transcriber.py <caminho_do_arquivo>")
        sys.exit(1)
    
    entrada = sys.argv[1]
    wav_file = converter_para_wav(entrada)
    
    try:
        resultado = ""
        for chunk in transcribe_audio(wav_file, "."):
            resultado += chunk + " "
        
        nome_saida = os.path.splitext(entrada)[0] + "_transcrito.txt"
        with open(nome_saida, "w", encoding="utf-8") as f:
            f.write(resultado)
        
        print(f"Transcrição concluída! Arquivo salvo em: {nome_saida}")
    
    finally:
        # Limpar arquivo temporário
        limpar_arquivo_temp(wav_file)