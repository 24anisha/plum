import click


from cli.add import add, add_bulk_json, add_bulk_jsonl
from cli.clean import clean
from cli.clone import clone
from cli.build import build
from cli.verify import verify
from cli.test import test
from cli.coverage import coverage
from cli.init import init
from cli.parse import parse
from cli.upgrade import upgrade


@click.group()
def main():
    """Plum CLI tool."""
    pass


main.add_command(add)
main.add_command(add_bulk_json)
main.add_command(add_bulk_jsonl)
main.add_command(clean)
main.add_command(clone)
main.add_command(build)
main.add_command(verify)
main.add_command(test)
main.add_command(coverage)
main.add_command(init)
main.add_command(parse)
main.add_command(upgrade)


if __name__ == '__main__':
    main()
