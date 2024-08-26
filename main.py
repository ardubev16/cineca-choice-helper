#!/usr/bin/env python3

import argparse
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import inquirer
import pandas as pd
import requests

COURSE_CATALOGUE_URL_TEMPLATE = "https://unitn.coursecatalogue.cineca.it/api/v1/corso/{aa}/{corso_cod}"
COURSE_URL_TEMPLATE = "https://unitn.coursecatalogue.cineca.it/insegnamenti/{aa}/{cod}/{ordinamento_aa}/{corso_percorso_id}/{corso_cod}"  # fmt: skip # noqa: E501


@dataclass
class Config:
    year: int
    lang: Literal["en", "it"]


class Keys:
    def __init__(self, lang: Literal["en", "it"]):
        self.des = f"des_{lang}"
        self.label = f"label_{lang}"
        self.periodo_didattico = f"periodo_didattico_{lang}"


def select_year() -> int:
    return inquirer.text("Select the Academic year", default=datetime.today().year)


class CourseChooser:
    def __init__(self, config: Config):
        self.year = config.year
        self.keys = Keys(config.lang)

    def get_cds(self) -> str:
        gruppi = requests.get(
            "https://unitn.coursecatalogue.cineca.it/api/v1/corsi",
            params={"anno": self.year, "minimal": "true"},
            timeout=30,
        ).json()

        group = self._select_with_des("Select the Degree type", gruppi)
        department = self._select_with_des("Select Department", group["subgroups"])
        return self._select_with_des("Select Course", department["cds"])["cdsSub"][0]["cod"]

    def get_course_catalogue(self, cod: str) -> pd.DataFrame:
        course_paths = requests.get(
            COURSE_CATALOGUE_URL_TEMPLATE.format(aa=self.year, corso_cod=cod),
            timeout=30,
        ).json()["percorsi"]
        courses = self._select_with_des("Select the study path", course_paths)
        return self._serialize_course_choices(courses)

    def _select_with_des(self, prompt: str, options: list[dict]) -> dict:
        choices = [o[self.keys.des] for o in options]
        choice = inquirer.list_input(prompt, choices=choices)

        return next(o for o in options if o[self.keys.des] == choice)

    def _serialize_course_choices(self, percorso: dict) -> pd.DataFrame:
        serialized = []
        for year in percorso["anni"]:
            for teaching in year["insegnamenti"]:
                intermidiate = []
                if not teaching["attivita"]:
                    intermidiate.append(
                        {
                            "Year": year["anno"],
                            "Teaching": teaching[self.keys.label],
                            "Semester": "",
                            "CFU": "",
                            "Name": "N/A",
                            "Link": "N/A",
                        },
                    )

                for activity in teaching["attivita"]:
                    link = COURSE_URL_TEMPLATE.format(**activity)
                    intermidiate.append(
                        {
                            "Year": year["anno"],
                            "Teaching": teaching[self.keys.label],
                            "Semester": activity.get(self.keys.periodo_didattico, ""),
                            "CFU": activity["crediti"],
                            "Name": activity[self.keys.des],
                            "Link": f'=HYPERLINK("{link}", "{activity["cod"]}")',
                        },
                    )
                intermidiate.sort(key=lambda a: a["Semester"])
                serialized.extend(intermidiate)

        return pd.DataFrame(serialized)


def save_to_xlsx(filename: str, df: pd.DataFrame) -> None:
    with pd.ExcelWriter(filename) as writer:
        df.to_excel(writer, sheet_name="Sheet1", index=False)
        for column in df:
            column_width = max(df[column].astype(str).map(len).max(), len(column))
            col_idx = df.columns.get_loc(column)
            writer.sheets["Sheet1"].set_column(col_idx, col_idx, column_width)

    print(f"Courses saved into {filename}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate an Excel file with the courses from UniTn to choose.")
    parser.add_argument("filename", help="Path in which to save the selected cds' courses.")
    parser.add_argument(
        "-l",
        "--lang",
        choices=["en", "it"],
        default="it",
        help="Choose the language to use for the description of the courses. (default: %(default)s)",
    )
    parser.add_argument(
        "-y",
        "--year",
        type=int,
        default=datetime.today().year,
        help="Starting academic year to use to list the courses. (default: %(default)s)",
    )
    args = parser.parse_args()

    config = Config(args.year, args.lang)
    print(
        "NOTE: if you don't know what to answer to the following questions take a look at: https://unitn.coursecatalogue.cineca.it/",
    )

    cc = CourseChooser(config)
    cod = cc.get_cds()
    courses = cc.get_course_catalogue(cod)

    save_to_xlsx(args.filename, courses)
