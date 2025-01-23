# Example: reuse your existing OpenAI setup
import os
from pathlib import Path
import json5
from retry import retry

from config import getconfig
from lib.md2docx_python.md2docx_python.src.md2docx_python import markdown_to_word

import typer  # see https://typer.tiangolo.com/tutorial/subcommands/
from typing_extensions import Annotated

from functions import call_ai_with_template, extract_json, writefile, clean_json, init_client, readfile, get_template
from jinja2 import Template
from chaptersapp import gatherPriorChapters, generateall

# bootstrap typer
app = typer.Typer(no_args_is_help=True)

# Point to the local server
client = init_client()

@retry(tries=getconfig("RETRY_COUNT"))
@app.command()
def create(
        name: Annotated[str, typer.Option(help="Folder name to save this to", prompt="Folder name for book")] = "",
        title: Annotated[str, typer.Option(help="Title of the book", prompt=True)] = "Choose something for me",
        description: Annotated[str, typer.Option(help="Description of the book", prompt="Description of the book")] = "Something interesting",
        themes: Annotated[
            str, typer.Option(help="Comma separated list of themes", prompt=True)] = "Love, friendship, and perseverance",
        genres: Annotated[str, typer.Option(help="Comma separated list of genres", prompt=True)] = "Teen fiction",
        booktype: Annotated[str, typer.Option(help="Type of book to create", prompt=True)] = "Novel",
        structure: Annotated[str, typer.Option(help="Structure to follow when outlining chapters", prompt="Story structure, such as seven point story, save the cat, heroes journey, etc")] = "Seven point story structure",
        additionalHelp: Annotated[str, typer.Option(help="Any additional coaching you wish to provide to the AI", prompt=True)] = ""
):
    rawResponse = call_ai_with_template(client, "noveloutline",
                                     {"title": title, "description": description, "themes": themes, "genres": genres,
                                      "booktype": booktype, "structure": structure, "additionalHelp": additionalHelp},
                                     ['#', '---', '```', '``'])
    bookoutlineraw = extract_json(rawResponse)
    try:
        bookoutline_cleaned = bookoutlineraw[:]
        bookoutline_cleaned = clean_json(client, bookoutlineraw[:])
    except Exception as e:
        print(e)
    finally:
        if name:
            Path("./books/" + name).mkdir(parents=True, exist_ok=True)
            writefile("./books/" + name + "/manifest.json", bookoutline_cleaned)
    list() # update books list in ui
    return bookoutline_cleaned

@retry(tries=getconfig("RETRY_COUNT"))
@app.command()
def generate(
        name: Annotated[str, typer.Option(help="Folder name to save this to", prompt="Folder name for book")] = "novel",
        title: Annotated[str, typer.Option(help="Title of the book", prompt=True)] = "Choose something for me",
        description: Annotated[str, typer.Option(help="Description of the book", prompt="Description of the book")] = "Something interesting",
        themes: Annotated[
            str, typer.Option(help="Comma separated list of themes", prompt=True)] = "Love, friendship, and perseverance",
        genres: Annotated[str, typer.Option(help="Comma separated list of genres", prompt=True)] = "Teen fiction",
        booktype: Annotated[str, typer.Option(help="Type of book to create", prompt=True)] = "Novel",
        structure: Annotated[str, typer.Option(help="Structure to follow when outlining chapters", prompt="Story structure, such as seven point story, save the cat, heroes journey, etc")] = "Seven point story structure",
        additionalHelp: Annotated[str, typer.Option(help="Any additional coaching you wish to provide to the AI", prompt=True)] = ""
):
    create(name, description, title, themes, genres, booktype, structure, additionalHelp)
    generateall(name)
    tomarkdown(name)
    toaudiobook(name)
    docxfilename = todocx(name)
    list() # update books list in ui
    return docxfilename

@app.command()
def list():
    books_dir = "./books"
    if hasattr(list, "books"): # note: list.books is used so changes propagate
        list.books.clear()
    else: 
        list.books = []
    for root, dirs, files in os.walk(books_dir):
        if "manifest.json" in files:
            book_name = root[len(books_dir) + 1:]
            print(book_name)
            list.books.append(book_name)
            # print(re.search("./books/(.+)", root).groups(0)[0])
    list.books = sorted(list.books)
    return list.books

@app.command()
def get(
        name: Annotated[str, typer.Argument(help="Folder name of book")],
):
    contents = readfile("./books/" + name + "/manifest.json")
    print(contents)
    return contents


@app.command()
def getcontents(
        name: Annotated[str, typer.Argument(help="Folder name of book")],
        format: Annotated[str, typer.Argument(help="markdown or audiobook")] = "markdown"
):
    return tomarkdown(name) if format == "markdown" else toaudiobook(name)

@app.command()
def tomarkdown(
name: Annotated[str, typer.Argument(help="Folder name of book")],
):
    data = readfile("books/" + name + "/manifest.json")
    manifest = json5.loads(data)
    chapters = gatherPriorChapters(name, len(manifest["chapters"]) + 1)
    manifest["chapters"] = chapters

    markdown = Template(get_template("markdown")).render(manifest)
    writefile("./books/" + name + "/book.md", markdown)
    print(markdown)
    return markdown

@app.command()
def toaudiobook(
name: Annotated[str, typer.Argument(help="Folder name of book")],
):
    data = readfile("books/" + name + "/manifest.json")
    manifest = json5.loads(data)
    chapters = gatherPriorChapters(name, len(manifest["chapters"]) + 1)
    manifest["chapters"] = chapters

    audiobook = Template(get_template("audiobook")).render(manifest)
    writefile("./books/" + name + "/audiobook.txt", audiobook)
    print(audiobook)
    return audiobook

@app.command()
def todocx(
name: Annotated[str, typer.Argument(help="Folder name of book")],
):
    docx_filename = "books/" + name + "/book.docx"
    markdown_to_word("books/" + name + "/book.md", docx_filename, "templates/template.docx")
    print("Outputted to " + docx_filename)
    return docx_filename
