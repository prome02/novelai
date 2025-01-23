# Example: reuse your existing OpenAI setup
import os
from pathlib import Path

import json5
import retry
import typer  # see https://typer.tiangolo.com/tutorial/subcommands/
from typing_extensions import Annotated

from config import getconfig
from retry import retry
from functions import call_ai_with_template, extract_json, readfile, writefile, clean_json, init_client

# bootstrap typer
app = typer.Typer(no_args_is_help=True)

# Point to the local server
client = init_client()

@app.command()
@retry(tries=getconfig("RETRY_COUNT"))
def summarize(
        name: Annotated[str, typer.Argument(help="Folder name to read book manifest from")],
        chapter: Annotated[int, typer.Argument(help="Chapter number to generate")],
        additionalHelp: Annotated[str, typer.Option(help="Any additional coaching you wish to provide to the AI")] = ""
):
    chaptercontents = readfile("./books/" + name + "/chapter" + str(chapter) + ".txt")
    data = readfile("books/" + name + "/manifest.json")
    manifest = json5.loads(data)
    manifest.update({
        "chapterName": manifest["chapters"][chapter-1]["name"],
        "chapter": chapter,
        "additionalHelp": additionalHelp,
        "chaptercontents": chaptercontents
    })

    chaptersummary = clean_json(client, extract_json(call_ai_with_template(client, "chaptersummary", manifest, ['```', '``'])))
    writefile("books/" + name + "/chapter" + str(chapter) + ".json", chaptersummary)
    print(chaptersummary)
    return chaptersummary

def gatherPriorChapters(name, chapter):
    priorchapters = []
    chapter = int(chapter)
    if (chapter > 1):
        for i in range(1, chapter):
            summary = json5.loads(readfile("books/" + name + "/chapter" + str(i) + ".json"))
            chaptercontents = readfile("books/" + name + "/chapter" + str(i) + ".txt")
            summary.update({
                "chapter": i,
                "chaptercontents": chaptercontents
            })
            priorchapters.append(summary)
    return priorchapters

@retry(tries=getconfig("RETRY_COUNT"))
@app.command()
def generate(
        name: Annotated[str, typer.Argument(help="Folder name to read book manifest from")],
        chapter: Annotated[str, typer.Argument(help="Chapter number to generate")],
        additionalHelp: Annotated[str, typer.Option(help="Any additional coaching you wish to provide to the AI")] = ""
):
    chapter = int(chapter)

    # load manifest and add on additional variables passed in
    data = readfile("books/" + name + "/manifest.json")
    manifest = json5.loads(data)
    manifest.update({
        "chapter": chapter,
        "additionalHelp": additionalHelp
    })

    # Get prior chapters and chapter outline
    priorChapters = gatherPriorChapters(name, chapter)
    manifest.update({"priorChapters": priorChapters})
    mergePriorChaptersWithManifest(manifest, priorChapters)

    # generate or get chapter outline
    chapterOutlineFilename = "books/" + name + "/chapter" + str(chapter) + ".outline.json"
    chapter_outline = None
    if Path(chapterOutlineFilename).is_file():
        chapterOutlineRaw = readfile(chapterOutlineFilename)
        chapter_outline = json5.loads(chapterOutlineRaw)
    else:
        chapter_outline = outline(name, chapter, additionalHelp)

    # Generate each section of outline
    chaptercontents = ""
    sectionssofar = []

    for section in chapter_outline["sections"]:
        # Generate next section
        manifest.update({
            "chaptercontents": chaptercontents,
            "section": section,
            "sectionssofar": sectionssofar,
            "sections": chapter_outline["sections"]
        })
        sectioncontents = call_ai_with_template(client, "generatechapter", manifest, ['#', '---', '```', '--', '``'])
        sectioncontents = sectioncontents.strip()

        # Summarize next section
        if chaptercontents != "":
            chaptercontents += "\n\n---\n\n"
        chaptercontents += sectioncontents
        section.update({
            "contents": sectioncontents
        })
        sectionssofar.append(section)

        # Output to file
        writefile("./books/" + name + "/chapter" + str(chapter) + ".txt", chaptercontents)

    print(chaptercontents)
    summarize(name, chapter)
    return chaptercontents

@retry(tries=getconfig("RETRY_COUNT"))
def mergePriorChaptersWithManifest(manifest, priorChapters):
    for priorChapter in priorChapters:
        if "characters" in priorChapter:
            for character in priorChapter["characters"]:
                if not character["name"] in list(map(lambda x: x["name"], manifest["characters"])) and "name" in character and "description" in character and character["name"] and character["description"] and character["name"].strip() != "" and character["description"].strip() != "":
                    manifest["characters"].append(character)
        if "settings" in priorChapter:
            for setting in priorChapter["settings"]:
                if not setting["name"] in list(map(lambda x: x["name"], manifest["settings"])) and "name" in setting and "description" in setting and setting["name"] and setting["description"] and setting["name"].strip() != "" and setting["description"].strip() != "":
                    manifest["settings"].append(setting)

@retry(tries=getconfig("RETRY_COUNT"))
@app.command()
def outline(
        name: Annotated[str, typer.Argument(help="Folder name to read book manifest from")],
        chapter: Annotated[str, typer.Argument(help="Chapter number to generate")],
        additionalHelp: Annotated[str, typer.Option(help="Any additional coaching you wish to provide to the AI")] = ""
):
    chapter = int(chapter)

    # load manifest and add on additional variables passed in
    data = readfile("books/" + name + "/manifest.json")
    manifest = json5.loads(data)
    manifest.update({
        "chapter": chapter,
        "additionalHelp": additionalHelp
    })

    # Gather context from prior chapters
    priorChapters = gatherPriorChapters(name, chapter)
    manifest.update({"priorChapters": priorChapters})
    mergePriorChaptersWithManifest(manifest, priorChapters)

    # Generate outline for chapter and save it
    chapterOutlineFilename = "books/" + name + "/chapter" + str(chapter) + ".outline.json"
    chapterOutlineResponse = call_ai_with_template(client, "generatechapteroutline", manifest, ["```", '``'])
    chapterOutlineRaw = clean_json(client, extract_json(chapterOutlineResponse))

    writefile(chapterOutlineFilename, chapterOutlineRaw)
    chapterOutline = json5.loads(chapterOutlineRaw)
    return chapterOutline

@retry(tries=getconfig("RETRY_COUNT"))
@app.command()
def refine(
        name: Annotated[str, typer.Argument(help="Folder name to read book manifest from")],
        chapter: Annotated[str, typer.Argument(help="Chapter number to generate")],
        method: Annotated[str, typer.Argument(help="Refinement method (conciseness, consistency, richness)")] = "richness",
        additionalHelp: Annotated[str, typer.Option(help="Any additional coaching you wish to provide to the AI")] = ""
):
    contents = readfile("books/" + name + "/chapter" + str(chapter) + ".txt")
    refined = call_ai_with_template(client, "refine/" + method, {
        "content": contents,
        "additionalHelp": additionalHelp
    }, ["```", '``'])
    print(refined)
    return refined

@retry(tries=getconfig("RETRY_COUNT"))
@app.command()
def refinemethodlist():
    methods_dir = "./templates/refine"
    methods = []
    for root, dirs, files in os.walk(methods_dir):
        if root == methods_dir:
            for file in files:
                if file.endswith(".jinja2"):
                    method_name = file[0:len(file)-len(".jinja2")]
                    print(method_name)
                    methods.append(method_name)
    return methods

@retry(tries=getconfig("RETRY_COUNT"))
@app.command()
def generateall(
        name: Annotated[str, typer.Argument(help="Folder name to read book manifest from")],
        additionalHelp: Annotated[str, typer.Option(help="Any additional coaching you wish to provide to the AI")] = ""
):
    # load manifest and add on additional variables passed in
    data = readfile("books/" + name + "/manifest.json")
    manifest = json5.loads(data)
    for i in range(1,  len(manifest["chapters"]) + 1):
        chapterSummaryFilename = "books/" + name + "/chapter" + str(i) + ".json"
        if not Path(chapterSummaryFilename).is_file():
            generate(name, i, additionalHelp)
        else:
            print("Skipping generating chapter " + str(i) + " as it already exists")

    from booksapp import tomarkdown, toaudiobook, todocx
    markdowndata = tomarkdown(name)
    toaudiobook(name)
    todocx(name)
    return markdowndata

@app.command()
def get(
        name: Annotated[str, typer.Argument(help="Folder name to save this to")],
        chapter: Annotated[int, typer.Argument(help="Chapter number to generate")]
):
    chapter_contents = readfile("./books/" + name + "/chapter" + str(chapter) + ".txt")
    print(chapter_contents)
    return chapter_contents
