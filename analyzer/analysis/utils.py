import json
import os
import time

from functools import partial

import click
from click import echo

from analyzer import settings
from analyzer.scheduling import AsyncMultiDocAnalyzer, SyncMultiDocAnalyzer


@click.command()
@click.option("-i", "--input-path", required=True,
              type=click.Path(exists=True, readable=True),
              help="The path where the document(s) to analyze are stored. "
              "Could either be a file or a directory.")
@click.option("-o", "--output-type", default="console",
              type=click.Choice(["html", "console"],
                                case_sensitive=False),
              help=("The output format (`console` will show the "
                    "10 most frequent terms only)"))
@click.option("-l", "--language", default="english",
              help="The language of the documents")
@click.option("-a", "--analyze-async", default=False, is_flag=True,
              help="Analyze documents asynchronously to allow for "
              "easier parallelization")
@click.option("-s", "--stem", default=False, is_flag=True,
              help="Analyze stems instead of words")
def cli(input_path, output_type, language, analyze_async, stem):
    """
    Implements the command line interface the user interacts with.
    """
    green = partial(click.style, bold=True, fg="green")
    bold = partial(click.style, bold=True)
    error = partial(click.style, bold=True, fg="red")

    echo(green("----------------------------"))
    echo(green("- Welcome to TermAnalyzer! -"))
    echo(green("----------------------------"))

    echo("\nHere's what you've told me so far:")

    documents_to_analyze = [os.path.join(input_path, path) for path in
                            os.listdir(input_path)]

    if not documents_to_analyze:
        echo(error("No documents to analyze :( Exiting.."))
        return

    echo(bold("\n- Documents to analyze:"))
    for doc in documents_to_analyze:
        echo("    * {doc}".format(doc=doc))

    output_name = output_type
    echo("- Analysis results will be written in: ", nl=False)
    if output_type == "html":
        output_name = "output." + output_type
    echo(bold(output_name))
    if analyze_async:
        echo(bold("- Will analyze asynchronously"))
        echo(click.style("[WARNING] Make sure you have celery workers "
                         "listening at {} otherwise tasks won't be consumed "
                         "(and files won't be analyzed)".format(
                             settings.CELERY_BROKER_URL),
                         bg="red", bold=True))
    if stem:
        echo(bold("- Will analyze stems instead of words"))

    if not click.confirm(bold("\nIs this correct?")):
        return

    if analyze_async:
        all_docs_analyzer = AsyncMultiDocAnalyzer(documents_to_analyze,
                                                  language, stem=stem)
    else:
        all_docs_analyzer = SyncMultiDocAnalyzer(documents_to_analyze,
                                                 language, stem=stem)

    in_progress, previously_completed = all_docs_analyzer.check_progress()

    with click.progressbar(length=len(documents_to_analyze),
                           label="Analyzing documents") as bar:
        while in_progress:
            all_docs_analyzer.perform_analysis()
            in_progress, completed = \
                all_docs_analyzer.check_progress()
            bar.update(completed - previously_completed)
            previously_completed = completed
            if analyze_async:
                # async analyzer doesn't block so we don't
                # want to keep the CPU busy-waiting until
                # tasks finish
                time.sleep(1)

    analysis_success, errors = all_docs_analyzer.analysis_success()
    if not analysis_success:
        click.echo(click.style("Analysis failed!"))
        click.echo("Could not process documents:")
        for doc in errors:
            click.echo("  * {}".format(doc))

    else:
        results = all_docs_analyzer.combine_output()
        click.echo(green("\nAnalysis completed!\n"))
        num = click.prompt("How many results do you want to show? "
                     "(Total: {})".format(len(results)), type=int, default=15)
        if output_type == "console":
            for term, details in results[:num]:
                data = ""
                data += "==============================\n"
                data += (" Term: {term} "
                         "(Occurencies: {num})\n").format(term=term,
                                                          num=details['count'])

                data += "==============================\n"
                data += " Documents:\n"
                for doc in details['documents']:
                    data += " * {}\n".format(doc)

                data += "==============================\n"
                data += " Sentences\n"
                for sentence in details['sentences']:
                    data += " * {}\n".format(sentence)
                click.echo_via_pager(data)
        else:
            click.echo("HTML printing not implemented yet..")
