#!/usr/bin/env python3

import argparse
from datetime import datetime
from functools import partial
from typing import Literal

import inquirer
import pandas as pd
import requests

UNIVERSITIES = [
    "unitn",
]

CINECA_BASE_URL = "https://{university}.coursecatalogue.cineca.it/{path}"
COURSE_CATALOGUE_PATH_TEMPLATE = "api/v1/corso/{aa}/{corso_cod}"
COURSE_PATH_TEMPLATE = "insegnamenti/{aa}/{cod}/{ordinamento_aa}/{corso_percorso_id}/{corso_cod}"


class Config:
    def __init__(self, year: int, lang: Literal["en", "it"]):
        self.year: int = year
        self.lang: Literal["en", "it"] = lang
        self.university: str = self._select_university()

    def _select_university(self) -> str:
        return inquirer.list_input("Select your University", choices=UNIVERSITIES)


class Keys:
    def __init__(self, lang: Literal["en", "it"]):
        self.des = f"des_{lang}"
        self.label = f"label_{lang}"
        self.periodo_didattico = f"periodo_didattico_{lang}"


class CourseChooser:
    def __init__(self, config: Config):
        self.year = config.year
        self.keys = Keys(config.lang)
        self.cineca_base_url = partial(CINECA_BASE_URL.format, university=config.university)

        print(f"NOTE: if you don't know what to answer to the following questions take a look at: {self.cineca_base_url(path="")}")  # fmt: skip # noqa: E501

    def get_degree(self) -> str:
        gruppi = requests.get(
            self.cineca_base_url(path="api/v1/corsi"),
            params={"anno": self.year, "minimal": "true"},
            timeout=30,
        ).json()

        group = self._select_with_des("Select the Degree type", gruppi)
        department = self._select_with_des("Select Department", group["subgroups"])
        return self._select_with_des("Select Course", department["cds"])["cdsSub"][0]["cod"]

    def get_course_catalogue(self, cod: str) -> pd.DataFrame:
        course_paths = requests.get(
            self.cineca_base_url(path=COURSE_CATALOGUE_PATH_TEMPLATE.format(aa=self.year, corso_cod=cod)),
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
                    link = self.cineca_base_url(path=COURSE_PATH_TEMPLATE.format(**activity))
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

    cc = CourseChooser(config)
    cod = cc.get_degree()
    courses = cc.get_course_catalogue(cod)

    save_to_xlsx(args.filename, courses)
