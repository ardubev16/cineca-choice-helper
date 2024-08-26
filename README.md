# Cineca course choice helper

A simple script that generates an Excel file to help you decide what courses to
attend in your next academic adventure.

## Compatibility

This tool is compatible with all Universities that use `*.coursecatalogue.cineca.it`.
The following are the tested universities, feel free to open issues / pull requests
to add more:

- [Unitn](https://www.unitn.it)

## Usage

- Clone the repository:

```bash
git clone https://github.com/ardubev16/cineca-choice-helper
```

- Create and source a virtual environment:

```bash
python3 -m venv venv && . venv/bin/activate
```

- Install the dependencies:

```bash
pip install -r requirements.txt
```

- Run the script with the required arguments, use the following command to print
  a help message:

```bash
python3 main.py -h
```
