# Example: reuse your existing OpenAI setup
import glob
import os
import re
import subprocess
from pathlib import Path

import json5
import typer  # see https://typer.tiangolo.com/tutorial/subcommands/
from typing_extensions import Annotated

from functions import readfile, writefile

# bootstrap typer
app = typer.Typer(no_args_is_help=True)

# SEE
cached_vars = {}
@app.command()
def generate_coqui(
    text: Annotated[str, typer.Option(help="Text to generate")],
    voice: Annotated[str, typer.Option(help="Preconfigured Voice ('Claribel Dervla', 'Daisy Studious', 'Gracie Wise', 'Tammie Ema', 'Alison Dietlinde', 'Ana Florence', 'Annmarie Nele', 'Asya Anara', 'Brenda Stern', 'Gitta Nikolina', 'Henriette Usha', 'Sofia Hellen', 'Tammy Grit', 'Tanja Adelina', 'Vjollca Johnnie', 'Andrew Chipper', 'Badr Odhiambo', 'Dionisio Schuyler', 'Royston Min', 'Viktor Eka', 'Abrahan Mack', 'Adde Michal', 'Baldur Sanjin', 'Craig Gutsy', 'Damien Black', 'Gilberto Mathias', 'Ilkin Urbano', 'Kazuhiko Atallah', 'Ludvig Milivoj', 'Suad Qasim', 'Torcull Diarmuid', 'Viktor Menelaos', 'Zacharie Aimilios', 'Nova Hogarth', 'Maja Ruoho', 'Uta Obando', 'Lidiya Szekeres', 'Chandra MacFarland', 'Szofi Granger', 'Camilla Holmström', 'Lilya Stainthorpe', 'Zofija Kendrick', 'Narelle Moon', 'Barbora MacLean', 'Alexandra Hisakawa', 'Alma María', 'Rosemary Okafor', 'Ige Behringer', 'Filip Traverse', 'Damjan Chapman', 'Wulf Carlevaro', 'Aaron Dreschner', 'Kumar Dahl', 'Eugenio Mataracı', 'Ferran Simen', 'Xavier Hayasaka', 'Luis Moray', 'Marcos Rudaski')")] = None,
    voice_wav: Annotated[str, typer.Option(help="TTS Voice (filename in voices directory)")] = "british-man-1.wav",
    model: Annotated[str, typer.Option(help="TTS Model (see 'tts --list_models')")] = "tts_models/multilingual/multi-dataset/xtts_v2",
    language: Annotated[str, typer.Option(help="Language (en)")] = "en",
    file_path: Annotated[str, typer.Option(help="Where to save file (out.wav)")] = "out.wav",
):
    from TTS.api import TTS
    import torch

    device = ("cuda" if torch.cuda.is_available() else "cpu") if "coqui_device" not in cached_vars else cached_vars["coqui_device"]
    print("Generating audio on device: " + device)
    cached_vars["coqui_device"] = device

    tts = TTS(model).to(device) if "tts" not in cached_vars else cached_vars["coqui_tts"]
    cached_vars["coqui_tts"] = tts

    print("Generating: " + text)

    voice = voice if voice is not None and voice != "" else None
    voice_wav = "voices/" + voice_wav if voice is None else None

    if text.strip() != "":
        tts.tts_to_file(
            text=text,
            speaker_wav=voice_wav,
            speaker=voice,
            language=language,
            file_path=file_path,
        )
        print("Generated " + file_path)
    else:
        print("Missing text to generate")
    return file_path

@app.command()
def generate_llasa3b(
    text: Annotated[str, typer.Option(help="Text to generate")],
    voice: Annotated[str, typer.Option(help="TTS Voice (filename in voices directory)")] = "british-man-1.wav",
    file_path: Annotated[str, typer.Option(help="Where to save file (out.wav)")] = "out.wav",
):
    # Load dependencies
    from xcodec2.modeling_xcodec2 import XCodec2Model
    from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
    import torch
    import torchaudio
    from scipy.io.wavfile import write

    # Calculate device
    device = ("cuda" if torch.cuda.is_available() else "cpu") if "llasa3b_device" not in cached_vars else cached_vars["llasa3b_device"]
    print("Generating audio on device: " + device)
    cached_vars["llasa3b_device"] = device

    # Init model, caching each step to improve performance in subsequent generations
    llasa_3b = 'srinivasbilla/llasa-3b'
    tokenizer = AutoTokenizer.from_pretrained(llasa_3b)

    model = AutoModelForCausalLM.from_pretrained(
        llasa_3b,
        trust_remote_code=True,
        device_map='cuda',
    ) if "llasa3b_model" not in cached_vars else cached_vars["llasa3b_model"]
    cached_vars["llasa3b_model"] = model

    model_path = "srinivasbilla/xcodec2"
    Codec_model = XCodec2Model.from_pretrained(model_path) if "llasa3b_model_path" not in cached_vars else cached_vars["llasa3b_model_path"]
    Codec_model.eval().cuda()
    cached_vars["llasa3b_model_path"] = Codec_model

    whisper_turbo_pipe = pipeline(
        "automatic-speech-recognition",
        model="openai/whisper-large-v3-turbo",
        torch_dtype=torch.float16,
        device=device,
    ) if "llasa3b_whisper_turbo_pipe" not in cached_vars else cached_vars["llasa3b_whisper_turbo_pipe"]
    cached_vars["llasa3b_whisper_turbo_pipe"] = whisper_turbo_pipe

    if text.strip() != "":
        waveform, sample_rate = torchaudio.load("voices/" + voice)
        if len(waveform[0]) / sample_rate > 15:
            print("Trimming audio to first 15secs.")
            waveform = waveform[:, :sample_rate * 15]

        # Check if the audio is stereo (i.e., has more than one channel)
        if waveform.size(0) > 1:
            # Convert stereo to mono by averaging the channels
            waveform_mono = torch.mean(waveform, dim=0, keepdim=True)
        else:
            # If already mono, just use the original waveform
            waveform_mono = waveform

        prompt_wav = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=16000)(waveform_mono)
        prompt_text = whisper_turbo_pipe(prompt_wav[0].numpy())['text'].strip()

        input_text = prompt_text + ' ' + text

        with torch.no_grad():
            # Encode the prompt wav
            vq_code_prompt = Codec_model.encode_code(input_waveform=prompt_wav)

            vq_code_prompt = vq_code_prompt[0, 0, :]
            # Convert int 12345 to token <|s_12345|>
            speech_ids_prefix = ids_to_speech_tokens(vq_code_prompt)

            formatted_text = f"<|TEXT_UNDERSTANDING_START|>{input_text}<|TEXT_UNDERSTANDING_END|>"

            # Tokenize the text and the speech prefix
            chat = [
                {"role": "user", "content": "Convert the text to speech:" + formatted_text},
                {"role": "assistant", "content": "<|SPEECH_GENERATION_START|>" + ''.join(speech_ids_prefix)}
            ]

            input_ids = tokenizer.apply_chat_template(
                chat,
                tokenize=True,
                return_tensors='pt',
                continue_final_message=True
            )
            input_ids = input_ids.to('cuda')
            speech_end_id = tokenizer.convert_tokens_to_ids('<|SPEECH_GENERATION_END|>')

            # Generate the speech autoregressively
            outputs = model.generate(
                input_ids,
                max_length=2048,  # We trained our model with a max length of 2048
                eos_token_id=speech_end_id,
                do_sample=True,
                top_p=1,
                temperature=0.8
            )
            # Extract the speech tokens
            generated_ids = outputs[0][input_ids.shape[1] - len(speech_ids_prefix):-1]

            speech_tokens = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)

            # Convert  token <|s_23456|> to int 23456
            speech_tokens = extract_speech_ids(speech_tokens)

            speech_tokens = torch.tensor(speech_tokens).cuda().unsqueeze(0).unsqueeze(0)

            # Decode the speech tokens to speech waveform
            gen_wav = Codec_model.decode_code(speech_tokens)

            # if only need the generated part
            gen_wav = gen_wav[:, :, prompt_wav.shape[1]:]

            write(file_path, 16000, gen_wav[0, 0, :].cpu().numpy())
            #return (16000, gen_wav[0, 0, :].cpu().numpy())

        print("Generated " + file_path)
    else:
        print("Missing text to generate")
    return file_path

@app.command()
def generate_kokoro(
    text: Annotated[str, typer.Option(help="Text to generate")],
    voice: Annotated[str, typer.Option(help="voice name")] = "af_heart",
    file_path: Annotated[str, typer.Option(help="Where to save file (out.wav)")] = "out.wav",
):
    from kokoro import KModel, KPipeline
    import gradio as gr
    import os
    import torch
    from scipy.io.wavfile import write

    CUDA_AVAILABLE = torch.cuda.is_available()

    models = {gpu: KModel().to('cuda' if gpu else 'cpu').eval() for gpu in [False] + ([True] if CUDA_AVAILABLE else [])} if "kokoro_models" not in cached_vars else cached_vars["kokoro_models"]
    cached_vars["kokoro_models"] = models

    pipelines = {lang_code: KPipeline(lang_code=lang_code, model=False, repo_id="hexgrad/Kokoro-82M") for lang_code in 'ab'} if "kokoro_pipelines" not in cached_vars else cached_vars['kokoro_pipelines']
    cached_vars['kokoro_pipelines'] = pipelines

    pipelines['a'].g2p.lexicon.golds['kokoro'] = 'kˈOkəɹO'
    pipelines['b'].g2p.lexicon.golds['kokoro'] = 'kˈQkəɹQ'

    pipeline = pipelines[voice[0]]
    pack = pipeline.load_voice(voice) if "kokoro_pack" not in cached_vars or cached_vars["kokoro_pack_voice"] != voice else cached_vars['kokoro_pack']
    cached_vars["kokoro_pack_voice"] = voice
    cached_vars["kokoro_pack"] = pack

    # if hosted as space, enforce char limit
    IS_DUPLICATE = not os.getenv('SPACE_ID', '').startswith('hexgrad/')
    CHAR_LIMIT = None if IS_DUPLICATE else 5000
    text = text if CHAR_LIMIT is None else text.strip()[:CHAR_LIMIT]

    use_gpu = CUDA_AVAILABLE
    speed = 1.0

    for _, ps, _ in pipeline(text, voice, speed):
        ref_s = pack[len(ps) - 1]
        try:
            if use_gpu:
                audio = forward_gpu(ps, ref_s, speed)
            else:
                audio = models[False](ps, ref_s, speed)
        except gr.exceptions.Error as e:
            if use_gpu:
                gr.Warning(str(e))
                gr.Info('Retrying with CPU. To avoid this error, change Hardware to CPU.')
                audio = models[False](ps, ref_s, speed)
            else:
                raise gr.Error(e)

        write(file_path, 24000, audio.numpy())
        return file_path
        #print(audio.numpy())
        #return (24000, audio.numpy()), ps
    return None

def forward_gpu(ps, ref_s, speed):
    from kokoro import KModel
    import torch

    CUDA_AVAILABLE = torch.cuda.is_available()
    models = {gpu: KModel().to('cuda' if gpu else 'cpu').eval() for gpu in [False] + ([True] if CUDA_AVAILABLE else [])}

    return models[True](ps, ref_s, speed)

def ids_to_speech_tokens(speech_ids):
    speech_tokens_str = []
    for speech_id in speech_ids:
        speech_tokens_str.append(f"<|s_{speech_id}|>")
    return speech_tokens_str

def extract_speech_ids(speech_tokens_str):
    speech_ids = []
    for token_str in speech_tokens_str:
        if token_str.startswith('<|s_') and token_str.endswith('|>'):
            num_str = token_str[4:-2]

            num = int(num_str)
            speech_ids.append(num)
        else:
            print(f"Unexpected token: {token_str}")
    return speech_ids

@app.command()
def chapter(
    book: Annotated[str, typer.Argument(help="Folder of book to generate")],
    chapter: Annotated[str, typer.Argument(help="Chapter to generate (number or all)")] = "all",
    coqui_voice: Annotated[str, typer.Option(help="Preconfigured Voice ('Claribel Dervla', 'Daisy Studious', 'Gracie Wise', 'Tammie Ema', 'Alison Dietlinde', 'Ana Florence', 'Annmarie Nele', 'Asya Anara', 'Brenda Stern', 'Gitta Nikolina', 'Henriette Usha', 'Sofia Hellen', 'Tammy Grit', 'Tanja Adelina', 'Vjollca Johnnie', 'Andrew Chipper', 'Badr Odhiambo', 'Dionisio Schuyler', 'Royston Min', 'Viktor Eka', 'Abrahan Mack', 'Adde Michal', 'Baldur Sanjin', 'Craig Gutsy', 'Damien Black', 'Gilberto Mathias', 'Ilkin Urbano', 'Kazuhiko Atallah', 'Ludvig Milivoj', 'Suad Qasim', 'Torcull Diarmuid', 'Viktor Menelaos', 'Zacharie Aimilios', 'Nova Hogarth', 'Maja Ruoho', 'Uta Obando', 'Lidiya Szekeres', 'Chandra MacFarland', 'Szofi Granger', 'Camilla Holmström', 'Lilya Stainthorpe', 'Zofija Kendrick', 'Narelle Moon', 'Barbora MacLean', 'Alexandra Hisakawa', 'Alma María', 'Rosemary Okafor', 'Ige Behringer', 'Filip Traverse', 'Damjan Chapman', 'Wulf Carlevaro', 'Aaron Dreschner', 'Kumar Dahl', 'Eugenio Mataracı', 'Ferran Simen', 'Xavier Hayasaka', 'Luis Moray', 'Marcos Rudaski')")] = None,
    coqui_voice_wav: Annotated[str, typer.Option(help="TTS Voice (filename in voices directory)")] = "british-man-1.wav",
    kokoro_voice: Annotated[str, typer.Option(help="Preconfigured Voice (See https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md)")] = None,
    llasa3b_voice_wav: Annotated[str, typer.Option(help="TTS Voice (filename in voices directory)")] = "british-man-1.wav",
):
    # Default values
    coqui_model = "tts_models/multilingual/multi-dataset/xtts_v2"
    language = "en"

    if coqui_voice == "":
        coqui_voice = None
    if coqui_voice_wav == "":
        coqui_voice_wav = None
    if kokoro_voice == "":
        kokoro_voice = None
    if llasa3b_voice_wav == "":
        llasa3b_voice_wav = None

    # Read contents and loop over chapters
    contents = readfile("./books/" + book + "/manifest.json")
    contents_parsed = json5.loads(contents)

    for idx, chapter_obj in enumerate(contents_parsed["chapters"]):
        if chapter != "all" and str(chapter) != str(int(idx)+1):
            #print("Skipping Chapter " + str(idx+1))
            continue
        try:
            # Read chapter contents, remove empty space, remove symbols that tend to cause issues.
            chapter_contents = readfile("./books/" + book + "/chapter" + str(idx+1) + ".txt")
            chapter_formatted = chapter_contents.replace("\r", "").replace("\n\n", "\n").replace("\n\n", "\n").replace("---", "...").replace("*", "")

            #filename = "books/" + book + "/audiobook-c" + ("{:03}".format(idx + 1)) + ".wav"
            #if not Path(filename).is_file():
            #    generate(chapter_formatted, voice, voice_wav, model, language, filename)
            #else:
            #    print("Skipping " + filename + " because already exists")

            # Alt method: Generates lines rather than chapters, but no need - xtts2 supports this natively
            lines = chapter_formatted.split("\n")

            # Add chapter header(s)
            chapter_name = re.sub(r'^Chapter \d+:?\s*', '', chapter_obj["name"], flags=re.IGNORECASE)
            lines.insert(0, f"Chapter {str(int(idx)+1)}. {chapter_name}..")
            
            # if first chapter add intro to book
            if idx == 0:
                lines.insert(0, f"{contents_parsed['title']}")
                if "author" in contents_parsed and contents_parsed["author"] is not None:
                    lines[0] += " by " + contents_parsed["author"]
                lines[0] += "... "

            # generate each line with selected model
            for line_idx, line in enumerate(lines):
                #print(line)
                #filename = f"books/{book}/audiobook-c{"{:03}".format(idx + 1)}-{"{:04}".format(line_idx)}.wav"
                filename = ("books/" + book + "/audiobook-c" + ("{:03}".format(idx + 1)) + "-" +
                    ("{:04}".format(line_idx)) + ".wav")
                if not Path(filename).is_file():
                    if coqui_voice is not None or coqui_voice_wav is not None:
                        generate_coqui(line, coqui_voice, coqui_voice_wav, coqui_model, language, filename)
                    elif kokoro_voice is not None:
                        generate_kokoro(line, kokoro_voice, filename)
                    elif llasa3b_voice_wav is not None:
                        generate_llasa3b(line, llasa3b_voice_wav, filename)
                    else:
                        generate_kokoro(line, "am_onyx", filename)
                else:
                    print("Skipping " + filename + " because already exists")
        except Exception as e:
            print(e)
            raise e

def run(command):
    result = subprocess.run(command, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("RAN: " + " ".join(command))
        print(result.stdout)
        print(result.stderr)

    return result.returncode == 0


@app.command()
def buildmp3(
    book: Annotated[str, typer.Argument(help="Folder of book to generate")],
    speed: Annotated[str, typer.Option(help="Speed to generate (1.1 is default)")] = "1.1"
):
    # Calculate location of files
    booksdir = "./books/" + book + "/"
    listfilename = booksdir + "list.txt"
    wavfilename = booksdir + "audiobook.wav"
    mp3filename = booksdir + "audiobook.mp3"

    Path(listfilename).unlink(missing_ok=True)
    Path(wavfilename).unlink(missing_ok=True)
    Path(mp3filename).unlink(missing_ok=True)

    # Build manifest of files to be combined
    pattern = f"{booksdir}audiobook-*.wav"
    files = glob.glob(pattern)
    files = sorted(files)
    files = [os.path.basename(file) for file in files]
    files = list(map(lambda x: f"file {x}", files))
    files_list = "\n".join(files)
    writefile(listfilename, files_list)

    # use ffmpeg to combine (note: requires ffmpeg be installed and on the path in your machine)
    print("Combining " + str(len(files)) + " Files into " + wavfilename)
    if run(["ffmpeg","-f","concat","-i",listfilename,"-c","copy",wavfilename]):
        print("Converting to mp3 and saving in " + mp3filename)
        if run(["ffmpeg","-i", wavfilename, "-filter:a", "atempo=" + str(speed), mp3filename]):
            print("Outputted to " + mp3filename)
            return mp3filename

    print("Failed")
    return None
    
    # Combining with ffmpeg: (if you want to do it manually and have more control...)
    # find audiobook-*.wav | sed 's:\ :\\\ :g'| sed 's/^/file /' > list.txt
    # ffmpeg -f concat -i list.txt -c copy audiobook.wav
    # ffmpeg -i audiobook.wav audiobook.mp3
    # ffmpeg -i audiobook.wav -filter:a "atempo=1.5" audiobook.mp3