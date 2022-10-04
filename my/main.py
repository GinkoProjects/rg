import argparse
import contextlib
import json
import logging
import random
import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Union

from my.commands import (HIDDEN_ARGUMENT, OPTIONAL_ARGUMENT, REQUIRED_ARGUMENT,
                         Command, CommandBinaryMode, Print,
                         SequentialProcessRunner, StdinConverter)
from my.plugins import loader

logger = logging.getLogger(__name__)


def run_process(process, args):
    prefix = ""
    args_dict = vars(args)
    if args.output_file:
        open_file_context = args.output_file.open("a")
    else:
        open_file_context = contextlib.nullcontext(sys.stdout)
        prefix = ">>> "

    if args.debug_output:
        debug_file_context = args.debug_output.open("a")
    else:
        debug_file_context = contextlib.nullcontext(sys.stderr)

    with open_file_context as f, debug_file_context as debug_out:
        for l in process.prepare(**args_dict).run(stdin=sys.stdin, stdout=debug_out, **args_dict):
            print(prefix, l, sep="", file=f)


def run_process_cli(args):
    if not args.background:
        process = args.retrieve_func(args.function_name)
        run_process(process, args)
    else:
        new_args = [arg for arg in sys.orig_argv if arg not in ["--bg", "--background"]]
        std_redir = {"stdin": subprocess.DEVNULL}
        if getattr(args, "output_file", None):
            out = args.output_file.open("a")
            std_redir.update(
                {
                    "stdout": out,
                    "stderr": out,
                }
            )

        sub = subprocess.Popen(new_args, **std_redir)


def create_argument_parser() -> ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage processes", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--debug", action="store_true", help="Open a ipdb shell")

    # Common arguments used for processes
    process_config_parser = argparse.ArgumentParser(description="processes config", add_help=False, allow_abbrev=False)
    process_config_parser.add_argument(
        "--background",
        "--bg",
        action="store_true",
        help="Run the process in the background instead of waiting for completion",
    )
    process_config_parser.add_argument(
        "--output-file", "--out", type=lambda p: Path(p).expanduser(), help="File to store the process output."
    )
    process_config_parser.add_argument(
        "--debug-output",
        default="/dev/null",
        type=lambda p: Path(p).expanduser(),
        help="Where to print the intermediate steps",
    )

    # run_parser = subparsers.add_parser("run", help="Run processes")
    # process_subparsers = parser.add_subparsers(dest="name", metavar="command")
    for plug_name, plug in loader.plugins.items():
        # process_parser = process_subparsers.add_parser(plug_name, parents=[process_config_parser])
        plug.add_arguments(parser, process_parser_kwargs={"parents": [process_config_parser]}, add_all_fields=True)

    parser.set_defaults(func=run_process_cli)

    return parser


def main():
    parser = create_argument_parser()

    args = parser.parse_args()
    if args.debug:
        import ipdb

        ipdb.set_trace()

    args.func(args)


if __name__ == "__main__":
    main()