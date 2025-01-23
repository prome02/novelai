# Example: reuse your existing OpenAI setup
import json5
import typer  # see https://typer.tiangolo.com/tutorial/subcommands/
from retry import retry
from typing_extensions import Annotated

import config
from config import getconfig
from functions import call_ai_with_template, init_client, call_ai_simple, readfile

# bootstrap typer
app = typer.Typer(no_args_is_help=True)

# Point to the local server
client = init_client()

@retry(tries=getconfig("RETRY_COUNT"))
@app.command()
def call(
        request: Annotated[str, typer.Argument(help="Request to run")],
        template: Annotated[str, typer.Option(help="Template to use")] = None,
        stop_at_section_block: Annotated[str, typer.Option(help="Character blocks to stop parsing at such as ```,``")] = '',
        loadfromfile: Annotated[bool, typer.Option(help="Load from file")] = False,
):
    stop_at_section_block_parsed = []
    if stop_at_section_block is not None and stop_at_section_block != "":
        stop_at_section_block_parsed = stop_at_section_block.split(",")

    if loadfromfile:
        request = readfile(request)

    if template is not None and template != "":
        metadata = { "request": request, "content": request }
        try:
            metadata.update(json5.loads(request))
        except Exception as e:
            if config.getconfig("NOVELAI_DEBUG"):
                print(e)

        with_template = call_ai_with_template(client, template, metadata, stop_at_section_block_parsed)
        print(with_template)
        return with_template
    else:
        simple = call_ai_simple(client, request, None, stop_at_section_block_parsed)
        print(simple)
        return simple
