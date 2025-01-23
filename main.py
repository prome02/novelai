# Example: reuse your existing OpenAI setup
import typer  # see https://typer.tiangolo.com/tutorial/subcommands/
from typing_extensions import Annotated

import glob
import os

import booksapp
import chaptersapp
import config
import openaiapp
import importlib
from config import getconfig, updateconfig

# bootstrap typer
app = typer.Typer(no_args_is_help=True)
app.add_typer(booksapp.app, name="books")
app.add_typer(chaptersapp.app, name="chapters")
app.add_typer(openaiapp.app, name="openai")

try:
    importlib.import_module("TTS")
    import audioapp
    app.add_typer(audioapp.app, name="audio")
except ImportError as e:
    print(e)
    if config.getconfig("NOVELAI_DEBUG"):
        print("Skipping audioapp")

# Gradio user interface
# def explore_novels():
#     import gradio as gr
#     with gr.Blocks() as interface:
#         with gr.Row():
#             file = gr.FileExplorer(root_dir="./books", ignore_glob="**/*.docx", file_count="single", height="100%")
#             file.change(fn=lambda: print(file.value))
#             code = gr.Code(lines=30, scale=2, language="markdown")
#     return interface

@app.command(help="Start Web UI")
def start(
        port: Annotated[str, typer.Option(help="Port number")] = getconfig("SERVER_PORT"),
        share: Annotated[bool, typer.Option(help="Share Public URL")] = False,
        inbrowser: Annotated[bool, typer.Option(help="Open Web Browser")] = False,
):
    import gradio as gr

    interfaces = []
    navs = []

    # Generate Novel
    interfaces.append(gr.Interface(
        fn=booksapp.generate,
        inputs= [
            gr.Textbox(label="Folder Name", value="novel"),
            gr.Textbox(label="Novel Title", value="Choose something for me"),
            gr.Textbox(label="Novel Description", value="Something interesting and inspiring", lines=4),
            gr.Textbox(label="Themes", value="Love, friendship, perseverance"),
            gr.Textbox(label="Genres", value="Teen fiction"),
            gr.Textbox(label="Book Type", value="Novel"),
            gr.Textbox(label="Book Story Structure", value="Seven point story structure"),
            gr.Textbox(label="Additional Help", value="", lines=4)
        ],
        outputs="file"
    ))
    navs.append("NovelAI")

    # Outline Novel
    interfaces.append(gr.Interface(
        fn=booksapp.create,
        inputs= [
            gr.Textbox(label="Folder Name", value="novel"),
            gr.Textbox(label="Novel Title", value="Choose something for me"),
            gr.Textbox(label="Novel Description", value="Something interesting and inspiring", lines=4),
            gr.Textbox(label="Themes", value="Love, friendship, perseverance"),
            gr.Textbox(label="Genres", value="Teen fiction"),
            gr.Textbox(label="Book Type", value="Novel"),
            gr.Textbox(label="Book Story Structure", value="Seven point story structure"),
            gr.Textbox(label="Additional Help", value="", lines=4)
        ],
        outputs="textbox"
    ))
    navs.append("Step 1: Outline Novel")

    # Generate Chapters
    interfaces.append(gr.TabbedInterface([
        gr.Interface(fn=chaptersapp.generateall,
                     inputs=[gr.Dropdown(label="Folder Name", choices=booksapp.list()),
                             gr.Textbox(label="Additional Help", value="")],
                     outputs="textbox"),
        gr.Interface(fn=chaptersapp.outline,
                     inputs=[gr.Dropdown(label="Folder Name", choices=booksapp.list()), "textbox",
                             gr.Textbox(label="Additional Help", value="")],
                     outputs="textbox"),
        gr.Interface(fn=chaptersapp.generate,
                     inputs=[gr.Dropdown(label="Folder Name", choices=booksapp.list()), "textbox",
                             gr.Textbox(label="Additional Help", value="")],
                     outputs="textbox"),
        gr.Interface(fn=chaptersapp.summarize,
                     inputs=[gr.Dropdown(label="Folder Name", choices=booksapp.list()), "textbox",
                             gr.Textbox(label="Additional Help", value="", lines=4)],
                     outputs="textbox"),
        gr.Interface(fn=chaptersapp.refine,
                     inputs=[gr.Dropdown(label="Folder Name", choices=booksapp.list()), "textbox",
                            gr.Dropdown(label="Refinement Method", choices=chaptersapp.refinemethodlist()),
                             gr.Textbox(label="Additional Help", value="", lines=4)],
                     outputs="textbox"),
    ], [
        "Step 2: Generate All Chapters", "Generate Chapter Outline", "Generate Chapter", "Generate Chapter Summary", "Refine Chapter",
    ]))
    navs.append("Step 2: Generate Novel")

    # Download
    interfaces.append(gr.TabbedInterface([
        gr.Interface(fn=booksapp.todocx, inputs=gr.Dropdown(label="Folder Name", choices=booksapp.list()),
                     outputs="file"),
        gr.Interface(fn=chaptersapp.get,
                     inputs=[gr.Dropdown(label="Folder Name", choices=booksapp.list()),
                             gr.Textbox(label="Chapter Number", value="")],
                     outputs="textbox"),
        gr.Interface(fn=booksapp.getcontents,
                     inputs=[gr.Dropdown(label="Folder Name", choices=booksapp.list()),
                             gr.Dropdown(label="Format", choices=["markdown", "audiobook"])],
                     outputs="textbox"),
        gr.Interface(fn=(lambda name: f"./books/{name}/audiobook.mp3"), inputs=gr.Dropdown(label="Folder Name", choices=booksapp.list()),
                     outputs="audio")
    ], [
        "Download Book", "Get Chapter", "Get Book", "Get MP3"
    ]))
    navs.append("Step 3: Download Novel")

    # Audio Functionality
    try:
        importlib.import_module("TTS")
        import audioapp

        voices = ['', 'Claribel Dervla', 'Daisy Studious', 'Gracie Wise', 'Tammie Ema', 'Alison Dietlinde', 'Ana Florence', 'Annmarie Nele', 'Asya Anara', 'Brenda Stern', 'Gitta Nikolina', 'Henriette Usha', 'Sofia Hellen', 'Tammy Grit', 'Tanja Adelina', 'Vjollca Johnnie', 'Andrew Chipper', 'Badr Odhiambo', 'Dionisio Schuyler', 'Royston Min', 'Viktor Eka', 'Abrahan Mack', 'Adde Michal', 'Baldur Sanjin', 'Craig Gutsy', 'Damien Black', 'Gilberto Mathias', 'Ilkin Urbano', 'Kazuhiko Atallah', 'Ludvig Milivoj', 'Suad Qasim', 'Torcull Diarmuid', 'Viktor Menelaos', 'Zacharie Aimilios', 'Nova Hogarth', 'Maja Ruoho', 'Uta Obando', 'Lidiya Szekeres', 'Chandra MacFarland', 'Szofi Granger', 'Camilla Holmström', 'Lilya Stainthorpe', 'Zofija Kendrick', 'Narelle Moon', 'Barbora MacLean', 'Alexandra Hisakawa', 'Alma María', 'Rosemary Okafor', 'Ige Behringer', 'Filip Traverse', 'Damjan Chapman', 'Wulf Carlevaro', 'Aaron Dreschner', 'Kumar Dahl', 'Eugenio Mataracı', 'Ferran Simen', 'Xavier Hayasaka', 'Luis Moray', 'Marcos Rudaski']
        voicewavs = glob.glob("voices/*.wav")
        voicewavs = sorted(voicewavs)
        voicewavs = [os.path.basename(file) for file in voicewavs]
        voicewavs.insert(0, "")

        navs.append("Step 4: Generate Audio")
        interfaces.append(gr.TabbedInterface([
            gr.Interface(fn=audioapp.generate, inputs=[
                gr.Textbox(label="Text", value="Please excuse my dear aunt sally"),
                gr.Dropdown(label="Voice", value='', choices=voices),
                gr.Dropdown(label="Voice Wav", value="british-man-1.wav", choices=voicewavs),
            ], outputs="audio"),
            gr.Interface(fn=audioapp.chapter, inputs=[
                gr.Dropdown(label="Folder Name", choices=booksapp.list()),
                     gr.Textbox(label="Chapter Number", value="all"),
                     gr.Dropdown(label="Voice", value='', choices=voices),
                     gr.Dropdown(label="Voice Wav", value="british-man-1.wav", choices=voicewavs),
                ],
                outputs="textbox"),
            gr.Interface(fn=audioapp.buildmp3,
                         inputs=[gr.Dropdown(label="Folder Name", choices=booksapp.list()),
                                 gr.Textbox(label="Speed", value="1.1")],
                         outputs="audio")
        ], [
            "Audio Tester", "Generate Chapter(s)", "Convert to MP3"
        ]))
    except ImportError as e:
        if config.getconfig("NOVELAI_DEBUG"):
            print(e)
            print("Skipping audioapp")

    # Config
    interfaces.append(gr.TabbedInterface([
        gr.Interface(fn=updateconfig, outputs="textbox",
                     inputs=gr.Matrix(
                         headers=["Key", "Value"],
                         datatype=["str", "str"],
                         row_count=len(config.getallconfig()),
                         label="Config Options",
                         value=[(k, v) for k, v in config.getallconfig().items()]
                     )),
        gr.Interface(fn=openaiapp.call, inputs=[
            gr.Textbox(label="Request (JSON if using template that requires multiple fields)", value="What is your name?"),
            gr.Textbox(label="Template Name", value="")
        ],
        outputs="textbox"),
    ], [
        "Config",
        "Test"
    ]))
    navs.append("Config")

    # Launch app!
    gr.TabbedInterface(
        interfaces,
        navs
    ).launch(server_port=int(port), show_error=True, share=share, inbrowser=inbrowser)

if __name__ == "__main__":
    app()

