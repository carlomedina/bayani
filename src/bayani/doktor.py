import os
from urllib.parse import unquote
import gzip
import base64
import re
import logging

log = logging.getLogger("doktor")


def convert_image_to_b64(markdown_chunk):
    clean = re.search("(!\[(.+?)\]\((.+?)\))(?= |$)", markdown_chunk).group(0)
    # todo: brittle. assumes that "](" does not exists on the file path.
    # seems to be the case in markdown parsing anyway
    parts = clean[2 : (len(clean) - 1)].split("](")
    alt, path = parts[0], parts[1]
    ext = os.path.splitext(path)[1]
    file = open(unquote(path), "rb")
    bytes = file.read()
    file.close()
    if ext == "svg":
        gzipped_bytes = gzip.compress(bytes)
        base64_bytes = base64.b64encode(gzipped_bytes)
    else:  # do not compress image binaries
        base64_bytes = base64.b64encode(bytes)
    base64_string = base64_bytes.decode("utf8")
    log.info(f"Converted image to string { unquote(path) }")
    return f"![b64|gzip|{ext}]({base64_string})"


def check_image_tag(line):
    search = re.search("!\[.+?\]\(.+?\)(?= |$)", line)
    if search:
        return search.group(0)
    return ""


def embed_image(line):
    replacement = ""
    check = check_image_tag(line)
    if check != "":
        replacement = convert_image_to_b64(check)
    return line.replace(check, replacement)


def process_markdown_file(input, output):
    """
    need to be in the WD of the markdown file
    """
    input_file = open(input, "r")
    lines = input_file.readlines()

    # remove notion metadata, return new list for lines
    start, end = find_metadata(lines)

    lines = remove_notion_metadata(lines, start, end)

    # embed image
    lines_image_embedded = [embed_image(line) for line in lines]

    output_file = open(output, "w")
    for line in lines_image_embedded:
        output_file.writelines(line)
    output_file.close()

    log.info(f"Processed { input } => { output }")
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
