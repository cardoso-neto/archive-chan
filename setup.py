from typing import List

import setuptools


def read_multiline_as_list(file_path: str) -> List[str]:
    with open(file_path) as fh:
        contents = fh.read().split("\n")
        if contents[-1] == "":
            contents.pop()
        return contents


with open("README.md", "r") as fh:
    long_description = fh.read()

requirements = read_multiline_as_list("requirements.txt")

# classifiers = read_multiline_as_list("classifiers.txt")

setuptools.setup(
    name="archive_chan",
    version="1.0.0.2021.01.17",
    author="Nei Cardoso de Oliveira Neto",
    author_email="nei.neto@hotmail.com",
    description="A fork of LameLemon's archive-chan maintained by cardoso-neto.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cardoso-neto/archive-chan",
    packages=setuptools.find_packages(where="src"),
    package_dir={"": "src"},  # not sure if this line should be here
    # classifiers=classifiers,
    keywords='archive data-hoarding web 3.0 4chan imageboard',
    entry_points = {
        'console_scripts': [
            'archive-chan=archive_chan:main',
            'archive-chan-build-index=thread_indexer:main'
        ],
    },
    python_requires=">=3.7",
    install_requires=requirements,
)
