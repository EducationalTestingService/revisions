"""
Given two text files, align and create an HTML and a JSON file
with information about sentence alignments and revisions.
"""

import os

import click
from revisions import AlignedText, Config, EditsHtml
from revisions.utils import tokenize_text, write_json
import pandas as pd


def create_html_file(
    file1,
    file2,
    min_par_sim,
    min_sent_sim,
    sim_slack,
    header1,
    header2,
    output_prefix=None,
    config=None,
    config_json=None,
    in_app=False,
    output_dir=None,
):
    if config is None:
        config = Config(config_json)

    if not (os.path.exists(file1) and os.path.exists(file2)):
        return None

    aligned_text = AlignedText(
        file1,
        file2,
        config["stop_words"],
        min_par_sim=min_par_sim,
        min_sent_sim=min_sent_sim,
        sim_slack=sim_slack,
        in_app=in_app,
    )

    edits_html = EditsHtml(aligned_text, config["templates"])
    if edits_html.num_edits == 0:
        return None

    # Include the legend for changes
    LEGEND = """
    <div style='margin-top:20px; font-size:16px;'>
        * Insertions are <span style="background-color:#FF99FF">highlighted in pink</span> <br>
        * Deletions are <span style="background-color:#CC99FF"><strike>striked and highlighted in purple</strike></span> <br>
        * Substitutions are <span style="background-color:#00FF99">highlighted in green</span>
    </div>
    """

    html_text = edits_html.get_html_text(header1, header2) + LEGEND
    if output_dir is None:
        output_dir = os.path.dirname(output_prefix)
    if output_dir:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    if output_prefix is None:
        output_info = [
            os.path.splitext(os.path.basename(file1))[0],
            os.path.splitext(os.path.basename(file2))[0],
            min_par_sim,
            min_sent_sim,
            sim_slack,
        ]
        output_prefix = "-".join(map(str, output_info))

    html_output_path = os.path.join(output_dir, output_prefix + ".html")
    with open(html_output_path, "w") as outfile:
        outfile.write(html_text)

    if not in_app:
        json_output_path = os.path.join(output_dir, output_prefix + ".json")
        write_json(json_output_path, edits_html.edits_json_dict)

    return html_text


@click.command()
@click.option(
    "--config_json",
    type=click.Path(exists=True),
    required=False,
    help="Path to the configuation file.",
)
@click.option(
    "--file1",
    type=click.Path(exists=True),
    required=True,
    help="Path to the text file of document version n.",
)
@click.option(
    "--file2",
    type=click.Path(exists=True),
    required=True,
    help="Path to the text file of document version n+1.",
)
@click.option(
    "--output_dir",
    type=click.Path(exists=False),
    required=True,
    help="Path to the output directory.",
)
@click.option(
    "--header1",
    type=str,
    default="",
    show_default=True,
    help="The header for document version n in the HTML.",
)
@click.option(
    "--header2",
    type=str,
    default="",
    show_default=True,
    help="The header for document version n+1 in the HTML.",
)
@click.option(
    "--min_par_sim",
    type=float,
    default=0.35,
    show_default=True,
    help="Min cosine similarity between two paragraphs for alignment.",
)
@click.option(
    "--min_sent_sim",
    type=float,
    default=0.4,
    show_default=True,
    help="Min similarity score between two sentences for alignment.",
)
@click.option(
    "--sim_slack",
    type=float,
    default=0.04,
    show_default=True,
    help="Max amount of similarity that can be lost after each step of incrementing N when finding for a 1-N or N-1 alignment.",
)
def create_html_file_wrapper(**kwargs):
    create_html_file(**kwargs)


if __name__ == "__main__":
    create_html_file_wrapper()
