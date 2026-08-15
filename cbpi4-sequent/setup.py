from os import path

from setuptools import find_packages, setup

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="cbpi4-sequent",
    version="0.1.0",
    description="CraftBeerPi4 plugin exposing Sequent Microsystems RTD and relay HATs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/BreakEvenBrewing/craftbeerpi-plugs",
    license="GPLv3",
    packages=find_packages(exclude=("tests", "tests.*")),
    include_package_data=True,
    package_data={"cbpi4_sequent": ["config.yaml"]},
    python_requires=">=3.9",
    install_requires=[
        "SMrtd==1.0.3",
        "SM8relind==1.0.4",
        "smbus2>=0.4.2",
    ],
)
