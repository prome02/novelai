# Example: reuse your existing OpenAI setup
from pathlib import Path
import glob
import os
import re

import json5
import typer  # see https://typer.tiangolo.com/tutorial/subcommands/
from typing_extensions import Annotated
import subprocess

from functions import readfile, writefile

# bootstrap typer
app = typer.Typer(no_args_is_help=True)

# SEE
cached_vars = {}
@app.command()
def generate(
    text: Annotated[str, typer.Option(help="Text to generate")],
    voice: Annotated[str, typer.Option(help="Preconfigured Voice ('Claribel Dervla', 'Daisy Studious', 'Gracie Wise', 'Tammie Ema', 'Alison Dietlinde', 'Ana Florence', 'Annmarie Nele', 'Asya Anara', 'Brenda Stern', 'Gitta Nikolina', 'Henriette Usha', 'Sofia Hellen', 'Tammy Grit', 'Tanja Adelina', 'Vjollca Johnnie', 'Andrew Chipper', 'Badr Odhiambo', 'Dionisio Schuyler', 'Royston Min', 'Viktor Eka', 'Abrahan Mack', 'Adde Michal', 'Baldur Sanjin', 'Craig Gutsy', 'Damien Black', 'Gilberto Mathias', 'Ilkin Urbano', 'Kazuhiko Atallah', 'Ludvig Milivoj', 'Suad Qasim', 'Torcull Diarmuid', 'Viktor Menelaos', 'Zacharie Aimilios', 'Nova Hogarth', 'Maja Ruoho', 'Uta Obando', 'Lidiya Szekeres', 'Chandra MacFarland', 'Szofi Granger', 'Camilla Holmström', 'Lilya Stainthorpe', 'Zofija Kendrick', 'Narelle Moon', 'Barbora MacLean', 'Alexandra Hisakawa', 'Alma María', 'Rosemary Okafor', 'Ige Behringer', 'Filip Traverse', 'Damjan Chapman', 'Wulf Carlevaro', 'Aaron Dreschner', 'Kumar Dahl', 'Eugenio Mataracı', 'Ferran Simen', 'Xavier Hayasaka', 'Luis Moray', 'Marcos Rudaski')")] = None,
    voice_wav: Annotated[str, typer.Option(help="TTS Voice (filename in voices directory)")] = "british-man-1.wav",
    model: Annotated[str, typer.Option(help="TTS Model (see 'tts --list_models')")] = "tts_models/multilingual/multi-dataset/xtts_v2",
    language: Annotated[str, typer.Option(help="Language (en)")] = "en",
    file_path: Annotated[str, typer.Option(help="Where to save file (out.wav)")] = "out.wav",
):
    from TTS.api import TTS
    import torch

    device = ("cuda" if torch.cuda.is_available() else "cpu") if "device" not in cached_vars else cached_vars["device"]
    print("Generating audio on device: " + device)
    cached_vars["device"] = device

    tts = TTS(model).to(device) if "tts" not in cached_vars else cached_vars["tts"]
    cached_vars["tts"] = tts

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
def chapter(
    book: Annotated[str, typer.Argument(help="Folder of book to generate")],
    chapter: Annotated[str, typer.Argument(help="Chapter to generate (number or all)")] = "all",
    voice: Annotated[str, typer.Option(help="Preconfigured Voice ('Claribel Dervla', 'Daisy Studious', 'Gracie Wise', 'Tammie Ema', 'Alison Dietlinde', 'Ana Florence', 'Annmarie Nele', 'Asya Anara', 'Brenda Stern', 'Gitta Nikolina', 'Henriette Usha', 'Sofia Hellen', 'Tammy Grit', 'Tanja Adelina', 'Vjollca Johnnie', 'Andrew Chipper', 'Badr Odhiambo', 'Dionisio Schuyler', 'Royston Min', 'Viktor Eka', 'Abrahan Mack', 'Adde Michal', 'Baldur Sanjin', 'Craig Gutsy', 'Damien Black', 'Gilberto Mathias', 'Ilkin Urbano', 'Kazuhiko Atallah', 'Ludvig Milivoj', 'Suad Qasim', 'Torcull Diarmuid', 'Viktor Menelaos', 'Zacharie Aimilios', 'Nova Hogarth', 'Maja Ruoho', 'Uta Obando', 'Lidiya Szekeres', 'Chandra MacFarland', 'Szofi Granger', 'Camilla Holmström', 'Lilya Stainthorpe', 'Zofija Kendrick', 'Narelle Moon', 'Barbora MacLean', 'Alexandra Hisakawa', 'Alma María', 'Rosemary Okafor', 'Ige Behringer', 'Filip Traverse', 'Damjan Chapman', 'Wulf Carlevaro', 'Aaron Dreschner', 'Kumar Dahl', 'Eugenio Mataracı', 'Ferran Simen', 'Xavier Hayasaka', 'Luis Moray', 'Marcos Rudaski')")] = None,
    voice_wav: Annotated[str, typer.Option(help="TTS Voice (filename in voices directory)")] = "british-man-1.wav",
    model: Annotated[str, typer.Option(help="TTS Model (see 'tts --list_models')")] = "tts_models/multilingual/multi-dataset/xtts_v2",
    language: Annotated[str, typer.Option(help="Language (en)")] = "en",
):
    if voice == "":
        voice = None
    if voice_wav == "":
        voice_wav = None

    contents = readfile("./books/" + book + "/manifest.json")
    contents_parsed = json5.loads(contents)

    for idx, chapter_obj in enumerate(contents_parsed["chapters"]):
        if chapter != "all" and str(chapter) != str(int(idx)+1):
            #print("Skipping Chapter " + str(idx+1))
            continue
        try:
            chapter_contents = readfile("./books/" + book + "/chapter" + str(idx+1) + ".txt")
            chapter_formatted = chapter_contents.replace("\r", "").replace("\n\n", "\n").replace("\n\n", "\n").replace("---", "...").replace("*", "")

            #filename = "books/" + book + "/audiobook-c" + ("{:03}".format(idx + 1)) + ".wav"
            #if not Path(filename).is_file():
            #    generate(chapter_formatted, voice, voice_wav, model, language, filename)
            #else:
            #    print("Skipping " + filename + " because already exists")

            # Alt method: Generates lines rather than chapters, but no need - xtts2 supports this natively
            lines = chapter_formatted.split("\n")

            # Add chapter header
            chapter_name = re.sub(r'^Chapter \d+:?\s*', '', chapter_obj["name"], flags=re.IGNORECASE)
            lines.insert(0, f"Chapter {str(chapter+1)}. {chapter_name}..")
            
            # if first chapter add intro to book
            if idx == 0:
                lines.insert(0, f"{contents_parsed['title']}")
                if contents_parsed["author"] is not None:
                    lines[0] += " by " + contents_parsed["author"]
                lines[0] += "... "

            # generate each line
            for line_idx, line in enumerate(lines):
                #print(line)
                filename = ("books/" + book + "/audiobook-c" + ("{:03}".format(idx + 1)) + "-" +
                    ("{:04}".format(line_idx)) + ".wav")
                if not Path(filename).is_file():
                    generate(line, voice, voice_wav, model, language, filename)
                else:
                    print("Skipping " + filename + " because already exists")
        except Exception as e:
            print(e)

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