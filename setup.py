from setuptools import setup, find_packages

setup(
    name="lisa",
    version="1.1.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "lisa=cli.main:cli_entrypoint",
        ],
    },
)
