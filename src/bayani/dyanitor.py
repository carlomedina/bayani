import os
import logging
import time
from pathlib import Path
import zipfile
import pandas as pd
import shutil
import re

log = logging.getLogger("dyanitor")


def extract_zip(input, output="."):
    zip_name = os.path.basename(input)
    folder_name, ext = os.path.splitext(zip_name)
    path_candidate = os.path.join(output, folder_name)
    path = path_candidate
    suffix = None
    # # create suffixed directory in case directory exists
    # #todo: evaluate this. perhaps overwriting the folder is better for idempotency
    # while os.path.exists(path):
    #     if suffix is None:
    #         suffix = 1
    #     else:
    #         suffix += 1
    #     path = f"{path_candidate}-{str(suffix)}"
    #
    # # create the folder
    if os.path.exists(path):
        shutil.rmtree(path)
        log.warning(f"Deleted existing directory { path }")
    os.makedirs(path)

    with zipfile.ZipFile(input, "r") as zip_ref:
        zip_ref.extractall(path)
    log.info(f"Extracted zip file into { path }")

    return path


def find_notion_db_directory(directory):
    # heuristically, notion seems to only return one csv per zip
    # for mvp, it will be assumed to be the case
    csvs = list(Path(directory).rglob("*.csv"))
    csv_directory = os.path.abspath(csvs[0])

    return csv_directory


def get_wanted_texts(notion_db, statuses):
    notion_db.columns = [column.lower() for column in notion_db.columns]
    notion_db.status = notion_db.status.str.lower()
    wanted_texts = notion_db.query("status in @statuses").text.tolist()
    return wanted_texts


def filter_texts(directory, statuses=["published", "reviewed"]):
    """
    filters only to the pages with publication-ready status.
    creates a new folder containing these pages (and their respective attachments)
    returns the directory of the filtered files
    """
    notion_db_directory = find_notion_db_directory(directory)
    notion_db = pd.read_csv(notion_db_directory)
    wanted_texts = get_wanted_texts(notion_db, statuses)

    # heuristically, folder containing the texts have the 'same' path
    # with the `.csv` removed
    notion_text_directory = notion_db_directory.replace(".csv", "")

    def _is_text_wanted(path, wanted_texts):
        return path.endswith(".md") and any(
            [path.startswith(wanted_text) for wanted_text in wanted_texts]
        )

    # create copy of directory
    filtered_dir = f"{ directory }-filtered"
    if os.path.exists(filtered_dir):
        shutil.rmtree(filtered_dir)
        log.warning(f"Deleted existing directory { filtered_dir }")
    os.makedirs(filtered_dir)

    for path in os.listdir(notion_text_directory):
        if _is_text_wanted(path, wanted_texts):
            path_to_copy = os.path.join(notion_text_directory, path)
            if os.path.isfile(path_to_copy):
                shutil.copy2(path_to_copy, filtered_dir)
                log.info(f"Copied { path } => { filtered_dir }")
            else:
                shutil.copy_tree(path_to_copy, filtered_dir)
                log.info(f"Copied all files from { path } => { filtered_dir }")

    return filtered_dir


def clean_texts(directory):
    # create "-cleaned" directory from "-filtered" directory
    cleaned_dir = re.sub("-filtered$", "-cleaned", directory)
    if os.path.exists(cleaned_dir):
        shutil.rmtree(cleaned_dir)
        log.warning(f"Deleted existing directory { cleaned_dir }")
    os.makedirs(cleaned_dir)

    for content in os.listdir(directory):
        path = os.path.join(directory, content)
        file_name = os.path.basename(path)
        text = open(path, "r")
        lines = text.readlines()

        # remove notion metadata, return new list for lines
        start, end = find_metadata(lines)
        lines = remove_notion_metadata(lines, start, end)

        output_path = os.path.join(cleaned_dir, file_name)
        output_text = open(output_path, "w")
        for line in lines:
            output_text.writelines(line)
        output_text.close()

        log.info(f"Processed { path } => { output_path }")
    return None


def find_metadata(lines, max_lines=20):
    """
    find contiguous lines with the following format `key: value`

    e.g.
    grade: 7
    Status: Draft
    Part: 10
    Syllabus: AB-XYZ1
    """

    def is_likely_metadata(line):
        if re.search("^.+?:.+", line):
            return True
        return False

    start = None
    end = None
    is_meta_prev = None
    # unlikely, but just in case
    # print(len(lines))
    if len(lines) == 0:
        return (start, end)

    for i in range(0, min(max_lines, len(lines))):
        if i > 0:  # only valid after the first line
            is_meta_prev = is_likely_metadata(lines[i - 1])
        is_meta_curr = is_likely_metadata(lines[i])
        # initialize
        if start is None and is_meta_curr:
            start = i
            end = i

        # inductive step
        if is_meta_prev and is_meta_curr:
            end = i
        elif end is not None and not is_meta_curr:
            break
    return (start, end)


def remove_notion_metadata(lines, start, end):
    if start is None:
        return lines
    else:
        return lines[:start] + lines[end + 1 :]
