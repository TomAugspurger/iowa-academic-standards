#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pymupdf",
#   "rich",
# ]
# ///


# 2015: https://educate.iowa.gov/media/8214/download?inline=
# 2025: https://educate.iowa.gov/media/10837/download?inline
import pathlib
import pymupdf
import re
import urllib.request
import subprocess
import rich.progress

import difflib


old_path = pathlib.Path("2015.pdf")
new_path = pathlib.Path("2025.pdf")

if not old_path.exists():
    urllib.request.urlretrieve(
        "https://educate.iowa.gov/media/8214/download?inline=", old_path
    )

if not new_path.exists():
    urllib.request.urlretrieve(
        "https://educate.iowa.gov/media/10837/download?inline", new_path
    )


def main():
    old = pymupdf.open(old_path)
    new = pymupdf.open(new_path)

    xpr_old = re.compile(r"HS-(PS|ESS|LS|ETS|A&P|AST)-?(\d+)-(\d+)\.")
    xpr_new = re.compile(r"HS-(PS|ESS|LS|ETS|A&P|AST)-?(\d+)-(\d+)\.?")

    clean = re.compile(r"\s\s+")
    quotes = re.compile("’")

    pages = [page for page in old if "HS-" in page.get_text()]
    old_records = []

    for page in rich.progress.track(pages, description="Parsing 2015"):
        page_text = page.get_text()
        m = xpr_old.search(page_text)
        groups = m.groups()
        group = f"HS-{groups[0]}" + "-".join(groups[1:])

        text = (
            page_text[m.end() :]
            .strip()
            .split("The performance expectation")[0]
            .replace("\n", " ")
            .strip()
        )
        text = text.split("[")[0].strip()
        text = text.rstrip("*")
        text = clean.sub(" ", text)
        text = quotes.sub("'", text)

        old_records.append((group, text))

    new_pages = [page for page in new if "HS-" in page.get_text()]

    new_records = []
    for page in rich.progress.track(new_pages, description="Parsing 2025"):
        tabs = page.find_tables()
        tables = [x.extract() for x in tabs.tables]

        for table in tables:
            for r in table:
                if r[0] and xpr_new.match(r[0]):
                    group, text, *_ = r

                    if group == "HS-PS-2-4":
                        # consistency
                        group = "HS-PS2-4"

                    if group == "HS-LS4-3.":
                        group = "HS-LS4-3"  # remove the .
                        text = r[2]

                    text = text.replace("\n", " ").strip()
                    text = quotes.sub("'", text)
                    text = text.replace(
                        "cost- benefit", "cost-benefit"
                    )  # bad line break
                new_records.append((group, text))

            # else:
            #     raise ValueError

    a = dict(old_records)
    b = dict(new_records)

    matched = set(a) & set(b)
    removed = set(a) - set(b)
    added = set(b) - set(a)

    def colorize_diff(diff):
        """Apply color formatting to diff output."""
        for line in diff:
            if line.startswith("+"):
                yield f"\033[32m{line}\033[0m"  # Green for additions
            elif line.startswith("-"):
                yield f"\033[31m{line}\033[0m"  # Red for deletions
            elif line.startswith("?"):
                yield f"\033[33m{line}\033[0m"  # Yellow for diff indicators
            else:
                yield line  # No color for unchanged lines

    def diff_strings(a: str, b: str):
        """Pretty-print the difference between two strings with colors."""
        diff = difflib.ndiff(a.splitlines(), b.splitlines())
        colored_diff = "\n".join(colorize_diff(diff))
        print(colored_diff)

    for k in sorted(matched):
        old_text = a[k]
        new_text = b[k]

        if old_text != new_text:
            print("-" * 80)
            print(k)
            diff_strings(old_text, new_text)

    # write out the old ones, for git
    p = pathlib.Path("standards/hs-science.md")
    p.parent.mkdir(parents=True, exist_ok=True)

    sections = [f"## {k}\n\n{a[k]}" for k in sorted(matched)]
    p.write_text("\n\n".join(sections))

    subprocess.check_call(["git", "add", "standards/hs-science.md"])
    subprocess.check_call(["git", "commit", "-m", "Added 2015 standards"])

    sections = [f"## {k}\n\n{b[k]}" for k in sorted(matched)]
    p.write_text("\n\n".join(sections))

    subprocess.check_call(["git", "add", "standards/hs-science.md"])
    subprocess.check_call(["git", "commit", "-m", "Added 2025 changes"])

    print("Removed standards:")
    for k in removed:
        print("-" * 80)
        v = a[k]
        print(f"{k}\n{v}", end="\n\n")

    print("Added standards:")
    for k in sorted(added):
        print("-" * 80)
        v = b[k]
        print(f"{k}\n{v}", end="\n\n")


if __name__ == "__main__":
    main()
