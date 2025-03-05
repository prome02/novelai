# Example: reuse your existing OpenAI setup
import glob
import json
import os
import time
from threading import Thread

import typer  # see https://typer.tiangolo.com/tutorial/subcommands/
from typing_extensions import Annotated

import audioapp
import booksapp
import chaptersapp
import config
import openaiapp
from config import getconfig, updateconfig

# bootstrap typer
app = typer.Typer(no_args_is_help=True)
app.add_typer(booksapp.app, name="books")
app.add_typer(chaptersapp.app, name="chapters")
app.add_typer(openaiapp.app, name="openai")
app.add_typer(audioapp.app, name="audio")

# Gradio user interface
# def explore_novels():
#     import gradio as gr
#     with gr.Blocks() as interface:
#         with gr.Row():
#             file = gr.FileExplorer(root_dir="./books", ignore_glob="**/*.docx", file_count="single", height="100%")
#             file.change(fn=lambda: print(file.value))
#             code = gr.Code(lines=30, scale=2, language="markdown")
#     return interface


#ui_thread = None
@app.command(help="Start Web UI")
def start(
        port: Annotated[str, typer.Option(help="Port number")] = getconfig("SERVER_PORT"),
        share: Annotated[bool, typer.Option(help="Share Public URL")] = False,
        inbrowser: Annotated[bool, typer.Option(help="Open Web Browser")] = False,
):
    #global ui_thread
    # auto restart ui thread if killed
    #while True:
        #ui_thread = Thread(target=startapp, args=(inbrowser, port, share))
        startapp(inbrowser, port, share)
        #while True:
        #    time.sleep(100000)
        #ui_thread.start()
        #print(ui_thread)
        #ui_thread.join()
        #print("Restarting...")

#def restart():
#    global ui_thread
##    print(ui_thread)
#    ui_thread.terminate()
#    return "Restarting..."

def startapp(inbrowser, port, share):
    import gradio as gr
    with gr.Blocks() as appuiblocks:
        # Generate Novel
        with gr.Tabs():
            with gr.Tab("NovelAI"):
                gr.Interface(
                    fn=booksapp.generate,
                    inputs=[
                        gr.Textbox(label="Book Folder Name", value="novel"),
                        gr.Textbox(label="Novel Title", value="Choose something for me"),
                        gr.Textbox(label="Novel Description", value="Something interesting and inspiring", lines=4),
                        gr.Textbox(label="Themes", value="Love, friendship, perseverance"),
                        gr.Textbox(label="Genres", value="Teen fiction"),
                        gr.Textbox(label="Book Type", value="Novel"),
                        gr.Textbox(label="Book Story Structure", value="Seven point story structure"),
                        gr.Textbox(label="Additional Help", value="", lines=4)
                    ],
                    outputs="file",
                    api_name="generate_book"
                )

            # Outline Novel
            with gr.Tab("Step 1: Outline Novel"):
                gr.Interface(
                    fn=booksapp.create,
                    inputs=[
                        gr.Textbox(label="Book Folder Name", value="novel"),
                        gr.Textbox(label="Novel Title", value="Choose something for me"),
                        gr.Textbox(label="Novel Description", value="Something interesting and inspiring", lines=4),
                        gr.Textbox(label="Themes", value="Love, friendship, perseverance"),
                        gr.Textbox(label="Genres", value="Teen fiction"),
                        gr.Textbox(label="Book Type", value="Novel"),
                        gr.Textbox(label="Book Story Structure", value="Seven point story structure"),
                        gr.Textbox(label="Additional Help", value="", lines=4)
                    ],
                    outputs="textbox",
                    api_name="generate_book_outline"
                )

            # Generate Chapters
            with gr.Tab("Step 2: Generate Chapters"):
                with gr.Tabs():
                    with gr.Tab("Step 2: Generate All Chapters"):
                        gr.Interface(fn=chaptersapp.generateall,
                                     inputs=[gr.Dropdown(label="Book Folder Name", allow_custom_value=True,
                                                         choices=booksapp.list()),
                                             gr.Textbox(label="Additional Help", value="")],
                                     outputs="textbox",
                                     api_name="generate_all_chapters")
                    with gr.Tab("Generate Chapter Outline"):
                        gr.Interface(fn=chaptersapp.outline,
                                     inputs=[gr.Dropdown(label="Book Folder Name", allow_custom_value=True,
                                                         choices=booksapp.list()), "textbox",
                                             gr.Textbox(label="Additional Help", value="")],
                                     outputs="textbox",
                                     api_name="generate_chapter_outline")
                    with gr.Tab("Generate Chapter"):
                        gr.Interface(fn=chaptersapp.generate,
                                     inputs=[gr.Dropdown(label="Book Folder Name", allow_custom_value=True,
                                                         choices=booksapp.list()), "textbox",
                                             gr.Textbox(label="Additional Help", value="")],
                                     outputs="textbox",
                                     api_name="generate_chapter")
                    with gr.Tab("Generate Chapter Summary"):
                        gr.Interface(fn=chaptersapp.summarize,
                                     inputs=[gr.Dropdown(label="Book Folder Name", allow_custom_value=True,
                                                         choices=booksapp.list()), "textbox",
                                             gr.Textbox(label="Additional Help", value="", lines=4)],
                                     outputs="textbox",
                                     api_name="generate_chapter_summary")
                    with gr.Tab("Refine Chapter"):
                        gr.Interface(fn=chaptersapp.refine,
                                     inputs=[gr.Dropdown(label="Book Folder Name", allow_custom_value=True,
                                                         choices=booksapp.list()), "textbox",
                                             gr.Dropdown(label="Refinement Method",
                                                         choices=chaptersapp.refinemethodlist()),
                                             gr.Textbox(label="Additional Help", value="", lines=4)],
                                     outputs="textbox",
                                     api_name="refine_chapter")

            # Download
            with gr.Tab("Step 3: Download"):
                with gr.Tabs():
                    with gr.Tab("Download Book"):
                        gr.Interface(fn=booksapp.todocx,
                                     inputs=gr.Dropdown(label="Book Folder Name", allow_custom_value=True,
                                                        choices=booksapp.list()),
                                     outputs="file",
                                     api_name="download_book")
                    with gr.Tab("Get Chapter"):
                        gr.Interface(fn=chaptersapp.get,
                                     inputs=[gr.Dropdown(label="Book Folder Name", allow_custom_value=True,
                                                         choices=booksapp.list()),
                                             gr.Textbox(label="Chapter Number", value="")],
                                     outputs="textbox",
                                     api_name="download_chapter")
                    with gr.Tab("Get Book"):
                        gr.Interface(fn=booksapp.getcontents,
                                     inputs=[gr.Dropdown(label="Book Folder Name", allow_custom_value=True,
                                                         choices=booksapp.list()),
                                             gr.Dropdown(label="Format", choices=["markdown", "audiobook"])],
                                     outputs="textbox",
                                     api_name="get_book")
                    with gr.Tab("Get MP3"):
                        gr.Interface(fn=(lambda name: f"./books/{name}/audiobook.mp3"),
                                     inputs=gr.Dropdown(label="Book Folder Name", allow_custom_value=True,
                                                        choices=booksapp.list()),
                                     outputs="audio",
                                     api_name="download_mp3")

            # Audio Functionality
            with gr.Tab("Step 4: Audio"):
                coqui_voices = ['', 'Claribel Dervla', 'Daisy Studious', 'Gracie Wise', 'Tammie Ema', 'Alison Dietlinde',
                          'Ana Florence', 'Annmarie Nele', 'Asya Anara', 'Brenda Stern', 'Gitta Nikolina',
                          'Henriette Usha', 'Sofia Hellen', 'Tammy Grit', 'Tanja Adelina', 'Vjollca Johnnie',
                          'Andrew Chipper', 'Badr Odhiambo', 'Dionisio Schuyler', 'Royston Min', 'Viktor Eka',
                          'Abrahan Mack', 'Adde Michal', 'Baldur Sanjin', 'Craig Gutsy', 'Damien Black',
                          'Gilberto Mathias', 'Ilkin Urbano', 'Kazuhiko Atallah', 'Ludvig Milivoj', 'Suad Qasim',
                          'Torcull Diarmuid', 'Viktor Menelaos', 'Zacharie Aimilios', 'Nova Hogarth', 'Maja Ruoho',
                          'Uta Obando', 'Lidiya Szekeres', 'Chandra MacFarland', 'Szofi Granger', 'Camilla Holmström',
                          'Lilya Stainthorpe', 'Zofija Kendrick', 'Narelle Moon', 'Barbora MacLean',
                          'Alexandra Hisakawa', 'Alma María', 'Rosemary Okafor', 'Ige Behringer', 'Filip Traverse',
                          'Damjan Chapman', 'Wulf Carlevaro', 'Aaron Dreschner', 'Kumar Dahl', 'Eugenio Mataracı',
                          'Ferran Simen', 'Xavier Hayasaka', 'Luis Moray', 'Marcos Rudaski']

                # See https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md#american-english
                kokoro_voices = ["af_alloy", "af_aoede", "af_bella", "af_heart", "af_jessica", "af_kore", "af_nicole",
                                 "af_nova", "af_river", "af_sarah", "af_sky", "am_adam", "am_echo", "am_eric",
                                 "am_fenrir", "am_liam", "am_michael", "am_onyx", "am_puck", "am_santa", "bf_alice",
                                 "bf_emma", "bf_isabella", "bf_lily", "bm_daniel", "bm_fable", "bm_george", "bm_lewis",
                                 #"ef_dora", "em_alex", "em_santa", "ff_siwis", "hf_alpha", "hf_beta", "hm_omega",
                                 #"hm_psi", "if_sara", "im_nicola", "jf_alpha", "jf_gongitsune", "jf_nezumi",
                                 #"jf_tebukuro", "jm_kumo", "pf_dora", "pm_alex", "pm_santa", "zf_xiaobei", "zf_xiaoni",
                                 #"zf_xiaoxiao", "zf_xiaoyi", "zm_yunjian", "zm_yunxi", "zm_yunxia", "zm_yunyang"
                                 ]

                voicewavs = sorted(
                    [os.path.basename(file) for file in glob.glob("voices/*.wav")] +
                    [os.path.basename(file) for file in glob.glob("voices/*.mp3")] +
                    [os.path.basename(file) for file in glob.glob("voices/.*.wav")] +
                    [os.path.basename(file) for file in glob.glob("voices/.*.mp3")]
                )
                voicewavs.insert(0, "")

                with gr.Tabs():
                    with gr.Tab("Coqui"):
                        gr.Interface(fn=audioapp.generate_coqui, inputs=[
                            gr.Textbox(label="Text", value="Please excuse my dear aunt sally"),
                            gr.Dropdown(label="Voice", value='', choices=coqui_voices, allow_custom_value=True),
                            gr.Dropdown(label="Voice Wav", value="british-man-1.wav", choices=voicewavs, allow_custom_value=True),
                        ], outputs="audio", api_name="test_audio")
                    with gr.Tab("Kokoro"):
                        gr.Interface(fn=audioapp.generate_kokoro, inputs=[
                            gr.Textbox(label="Text", value="Please excuse my dear aunt sally"),
                            gr.Dropdown(label="Voice", value='', choices=kokoro_voices, allow_custom_value=True)
                        ], outputs="audio", api_name="test_audio")
                    with gr.Tab("Llasa3b"):
                        gr.Interface(fn=audioapp.generate_llasa3b, inputs=[
                            gr.Textbox(label="Text", value="Please excuse my dear aunt sally"),
                            gr.Dropdown(label="Voice", value='british-man-1.wav', choices=voicewavs, allow_custom_value=True),
                        ], outputs="audio", api_name="test_audio")
                    with gr.Tab("Generate Chapter(s)"):
                        gr.Interface(
                            fn=audioapp.chapter,
                            inputs=[
                                gr.Dropdown(label="Book Folder Name", allow_custom_value=True, choices=booksapp.list()),
                                gr.Textbox(label="Chapter Number", value="all"),
                                gr.Dropdown(label="Coqui - Voice", value='', choices=coqui_voices),
                                gr.Dropdown(label="Coqui - Voice Wav", value="", choices=voicewavs),
                                gr.Dropdown(label="Kokoro - Voice", value='', choices=kokoro_voices),
                                gr.Dropdown(label="Llasa3b - Voice Wav", value="", choices=voicewavs),
                            ],
                            outputs="textbox",
                            api_name="generate_audio_chapters"
                        )
                    with gr.Tab("Convert to MP3"):
                        gr.Interface(
                            fn=audioapp.buildmp3,
                            inputs=[
                                gr.Dropdown(label="Book Folder Name", allow_custom_value=True, choices=booksapp.list()),
                                gr.Textbox(label="Speed (1.0 is normal)", value="1.0"),
                                gr.Textbox(label="Frequency Shift (1.0 is none)", value="1.0")
                            ],
                            outputs="audio",
                            api_name="compile_mp3"
                        )

            # Stub/Import Book Functionality
            with gr.Tab("Stub"):
                with gr.Tabs():
                    with gr.Tab("Stub Book"):
                        interface = gr.Interface(
                            fn=booksapp.stub,
                            inputs=[
                                gr.Textbox(label="Book Folder Name", value="novel"),
                                gr.Textbox(label="Novel Title", value="Choose something for me"),
                                gr.Textbox(label="Novel Description", value="Something interesting and inspiring",
                                           lines=4),
                                gr.Textbox(label="Themes", value="Love, friendship, perseverance"),
                                gr.Textbox(label="Genres", value="Teen fiction"),
                                gr.Textbox(label="Book Type", value="Novel"),
                                gr.Textbox(label="Lore", value="", lines=4),
                                gr.Textbox(label="Settings Count", value="3"),
                                gr.Textbox(label="Character Count", value="3"),
                                gr.Textbox(label="Chapter Count", value="10"),
                            ],
                            outputs=["textbox"],
                            api_name="stub_book"
                        )
                    with gr.Tab("Stub Chapter(s)"):
                        gr.Interface(
                            fn=chaptersapp.stub,
                            inputs=[
                                gr.Dropdown(label="Book Folder Name", allow_custom_value=True, choices=booksapp.list(),
                                            elem_classes=["book_folder_name"]),
                                gr.Textbox(label="Chapter to Generate", value="all"),
                                gr.Textbox(label="Section Count", value="3"),
                                gr.Checkbox(label="Create chapterx.txt files for importing chapters. ", value=False)
                            ],
                            outputs="textbox",
                            api_name="stub_chapters"
                        )

            # Config
            with gr.Tab("Config"):
                with gr.Tabs():
                    with gr.Tab("Config"):
                        def config_submit(c):
                            updateconfig(c)
                            #Thread(target=lambda: time.sleep(500) and appuiblocks.close(), args=()).start()
                            #print("APP UI:")
                            #print(appui)
                            #start()
                            return "Saved. Note that changing server port will not work. "
                            #return restart()
                        gr.Interface(fn=config_submit, outputs="textbox",
                                     inputs=gr.Matrix(
                                         headers=["Key", "Value"],
                                         datatype=["str", "str"],
                                         row_count=len(config.getallconfig()),
                                         label="Config Options",
                                         value=[(k, v) for k, v in config.getallconfig().items()]
                                     ))
                    with gr.Tab("Test"):
                        gr.Interface(
                            fn=openaiapp.call, inputs=[
                                gr.Textbox(label="Request (JSON if using template that requires multiple fields)",
                                           value="What is your name?"),
                                gr.Textbox(label="Template Name", value="")
                            ],
                            outputs="textbox",
                            api_name="test_llm")
                    # with gr.Tab("Reload"):
                    #     gr.Interface(
                    #         inputs=[]
                    #         outputs=["text"],
                    #         fn=lambda:
                    #     )
    # Launch app!
    appuiblocks.launch(server_port=int(port), show_error=True, share=share, inbrowser=inbrowser, show_api=True)

if __name__ == "__main__":
    app()

