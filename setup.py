"""A setuptools based setup module.

See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://github.com/pypa/sampleproject
"""

from setuptools import setup, find_packages
from os import path
import re

from io import open

HERE = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(HERE, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

VERSIONFILE=path.join(HERE, "plum", "_version.py")
V_MATCH = re.match(
        r"^__version__ = ['\"]([^'\"]*)['\"]",
        open(VERSIONFILE, "rt").read()
)
if V_MATCH:
    VERSTR = V_MATCH.group(1)
else:
    raise RuntimeError("Unable to find version string in %s" % VERSIONFILE)


setup(
    name="plum",  # Required

    version=VERSTR,  # Required

    description="Pipeline for programmatically interacting with JS, TS, Python, Java and C# repos.",  # Optional
    long_description=long_description,  # Optional
    long_description_content_type="text/markdown",  # Optional (see note above)
    packages=find_packages(exclude=["contrib", "docs", "test"]),  # Required
    python_requires=">=3.6, <4",
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "plum=cli.entry:main",
        ],
    },
    install_requires=[
            "autopep8>=1.4.4",
            "click>=8.1.7",
            "coverage>=7.2.7",
            "filelock>=3.13.1",
            "GitPython>=3.1.40",
            "inflection>=0.5.1",
            "lxml>=4.9.4",
            "openai>=0.25.0",
            "pdoc3>=0.10.0",
            "pycodestyle>=2.9.1",
            "pydocstyle>=6.1.1",
            "pydantic>=2.5.3",
            "pynpm>=0.1.2",
            "pytest>=7.1.3",
            "pytest-json-report>=1.5.0",
            "regex>=2022.9.13",
            "requests>=2.28.1",
            "source-parser>=1.0.4",
            "toml>=0.10.2",
            "tqdm>=4.64.1",
            "tenacity>=8.1.0",
            "tree-sitter>=0.20.1",
            "xmltodict>=0.13.0"
    ],
)
