"""Deposit a verification export on Zenodo: `linkage release zenodo`.

Through the REST API, with a DOI reserved BEFORE the PDF is frozen, so that the released PDF can
print its own version DOI. Ported from `spatial-hemigroup-scale-space`'s
`scripts/zenodo-release.py` (ADR-0001 step 5); it reads the export directory alone, so it needs
no `linkage.toml` and can be run from anywhere.

Why not Zenodo's GitHub integration alone: the integration mints the DOI when the GitHub release
is made, so the PDF inside the release cannot contain it; and for a record that was first
deposited by hand, a release through the integration starts a NEW concept DOI instead of adding a
version. The API does both: a new version of an existing record, and a reserved DOI. (The
integration can still be switched on for an export repository that has no deposit yet;
`.zenodo.json` in the export is what it reads.)

Three steps, run by the author, in this order:

  1. reserve   create a draft deposition (or a draft new version of --record), set its metadata
               from <export>/.zenodo.json, and print the reserved DOI. Nothing is public yet.
               The state is written to <export>/.zenodo-deposition.json (ids and DOI, no secret).
               Put the DOI into the paper (date line, the section that names the export), rebuild,
               re-export, tag.
  2. upload    upload the release files into the draft: the PDF at the export's root and a zip of
               the export's tagged tree (git archive), or the files given with --file.
  3. publish   publish the draft. This is irreversible: a published Zenodo record cannot be
               deleted, only superseded by a new version. The step asks for the word "publish".

  status       show the draft's state and files;  discard  delete an unpublished draft.

The token is read from the environment and is never written anywhere:
    ZENODO_TOKEN            for zenodo.org           (scopes: deposit:write, deposit:actions)
    ZENODO_SANDBOX_TOKEN    for sandbox.zenodo.org   (use --sandbox; test here first)
Create it at  https://zenodo.org/account/settings/applications/tokens/new/  (or the sandbox's).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

STATE = ".zenodo-deposition.json"


class ZenodoError(RuntimeError):
    """A fault the step cannot go on from; the CLI prints it and exits 2."""


def base(sandbox: bool) -> str:
    return "https://sandbox.zenodo.org/api" if sandbox else "https://zenodo.org/api"


def token(sandbox: bool) -> str:
    name = "ZENODO_SANDBOX_TOKEN" if sandbox else "ZENODO_TOKEN"
    t = os.environ.get(name, "").strip()
    if not t:
        raise ZenodoError(
            f"{name} is not set. Create a personal access token with the scopes deposit:write "
            f"and deposit:actions and export it in this shell; linkage never stores it.")
    return t


def call(method: str, url: str, tok: str, data=None, raw: bytes | None = None,
         ctype="application/json"):
    body = raw if raw is not None else (
        json.dumps(data).encode("utf-8") if data is not None else None)
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", "Bearer " + tok)
    if body is not None:
        req.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            text = r.read().decode("utf-8")
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise ZenodoError(f"Zenodo answered {e.code} to {method} {url}\n{detail}") from e


def load_state(export: Path) -> dict:
    p = export / STATE
    if not p.exists():
        raise ZenodoError(f"no {STATE} in {export}: run `linkage release zenodo reserve` first")
    return json.loads(p.read_text(encoding="utf-8"))


def save_state(export: Path, st: dict) -> None:
    (export / STATE).write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")


def deposit_gate(export: Path, st: dict, pdfs: list[Path]) -> list[str]:
    """The faults that keep an export from being deposited: a DRAFT marker, a PDF whose first
    page says it is a working draft, or one that does not print the reserved DOI."""
    faults = []
    if (export / "DRAFT").exists():
        faults.append("the export carries a DRAFT file: it was written with "
                      "`linkage release export --draft`")
    for pdf in pdfs:
        try:
            first = subprocess.run(["pdftotext", "-l", "1", str(pdf), "-"], capture_output=True,
                                   text=True, encoding="utf-8", errors="replace",
                                   check=True).stdout
        except (OSError, subprocess.CalledProcessError):
            faults.append(f"pdftotext is not available, so the first page of {pdf.name} could "
                          f"not be read")
            continue
        flat = " ".join(first.split()).lower()
        if "working draft" in flat or "not yet released" in flat:
            faults.append(f"the first page of {pdf.name} says it is a working draft")
        if st["doi"].lower() not in flat:
            faults.append(f"the first page of {pdf.name} does not print the reserved DOI "
                          f"{st['doi']}")
    return faults


def release_gate(export: Path, st: dict, pdfs: list[Path]) -> None:
    """Refuse a build that is not a release, outside the sandbox.

    The released PDF prints its date, its version and the DOI reserved for it; a build that says
    "working draft" reached a tag once and a sandbox deposit once. On the sandbox the faults are
    printed and the step goes on, since a sandbox DOI (10.5072/...) is never printed by a paper.
    """
    faults = deposit_gate(export, st, pdfs)
    if not faults:
        print("release gate: the PDF prints the reserved DOI and no draft line")
        return
    print("release gate:")
    for f in faults:
        print("    -", f)
    if st["sandbox"]:
        print("    (sandbox: going on all the same)")
        return
    raise ZenodoError(
        "refused on zenodo.org. Put the date, the version and the DOI on the paper's date line, "
        "rebuild, re-export with --doi, and run this step again (docs/RELEASE.md).")


def cmd_reserve(a) -> int:
    export = Path(a.export)
    meta_path = export / ".zenodo.json"
    if not meta_path.exists():
        raise ZenodoError(f"{meta_path} is missing: it is written by `linkage release export`")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if (export / STATE).exists() and not a.force:
        raise ZenodoError(f"{STATE} already exists in {export} (a draft is open). Use `status`, "
                          f"or `discard`, or --force to open another.")
    tok, api = token(a.sandbox), base(a.sandbox)
    if a.record:
        # a new version of an existing record: the draft inherits the old files, which are removed
        r = call("POST", f"{api}/deposit/depositions/{a.record}/actions/newversion", tok)
        draft_url = r["links"]["latest_draft"]
        dep = call("GET", draft_url, tok)
        for f in dep.get("files", []):
            call("DELETE", f"{api}/deposit/depositions/{dep['id']}/files/{f['id']}", tok)
    else:
        dep = call("POST", f"{api}/deposit/depositions", tok, data={})
    meta["prereserve_doi"] = True
    dep = call("PUT", f"{api}/deposit/depositions/{dep['id']}", tok, data={"metadata": meta})
    doi = (dep.get("metadata", {}).get("prereserve_doi") or {}).get("doi") or dep.get("doi", "")
    st = {"sandbox": a.sandbox, "id": dep["id"], "doi": doi, "bucket": dep["links"].get("bucket"),
          "html": dep["links"].get("html"), "new_version_of": a.record}
    save_state(export, st)
    print("draft deposition", dep["id"], "opened; nothing is public")
    print("reserved DOI:", doi)
    print("edit page:   ", st["html"])
    print(f"state written to {export / STATE} (add it to .gitignore or commit it; it holds no "
          f"secret)")
    return 0


def cmd_upload(a) -> int:
    export = Path(a.export)
    st = load_state(export)
    tok = token(st["sandbox"])
    files = [Path(f) for f in (a.file or [])]
    if not files:
        pdfs = sorted(export.glob("*.pdf"))
        if not pdfs:
            raise ZenodoError("no PDF at the export's root and no --file given")
        files += pdfs
        if a.tag:
            zip_path = export / f"{export.name}-{a.tag}.zip"
            subprocess.run(["git", "-C", str(export), "archive", "--format=zip",
                            f"--prefix={export.name}-{a.tag}/", "-o", str(zip_path), a.tag],
                           check=True)
            files.append(zip_path)
        else:
            print("no --tag: the source tree is not uploaded, only the PDF")
    release_gate(export, st, [f for f in files if f.suffix == ".pdf"])
    # The export is written again between `reserve` and `upload` (the DOI goes into the paper),
    # so the draft's metadata is set again from the .zenodo.json that is there now.
    meta = json.loads((export / ".zenodo.json").read_text(encoding="utf-8"))
    meta["prereserve_doi"] = True
    call("PUT", f"{base(st['sandbox'])}/deposit/depositions/{st['id']}", tok,
         data={"metadata": meta})
    print("metadata set from .zenodo.json: version", meta.get("version"), "| date",
          meta.get("publication_date"))
    for f in files:
        print("uploading", f.name, f"({f.stat().st_size} bytes)")
        call("PUT", f"{st['bucket']}/{f.name}", tok, raw=f.read_bytes(),
             ctype="application/octet-stream")
    print("uploaded; check the draft at", st["html"])
    return 0


def cmd_status(a) -> int:
    st = load_state(Path(a.export))
    dep = call("GET", f"{base(st['sandbox'])}/deposit/depositions/{st['id']}",
               token(st["sandbox"]))
    print("id", dep["id"], "| state:", dep.get("state"), "| submitted:", dep.get("submitted"))
    print("DOI:", st["doi"], "|", st["html"])
    for f in dep.get("files", []):
        print("  file:", f.get("filename"), f.get("filesize"))
    return 0


def cmd_publish(a) -> int:
    export = Path(a.export)
    st = load_state(export)
    where = "the SANDBOX" if st["sandbox"] else "zenodo.org"
    release_gate(export, st, sorted(export.glob("*.pdf")))
    print(f"About to publish deposition {st['id']} on {where} with DOI {st['doi']}.")
    print("A published record cannot be deleted. Type the word publish to go on:")
    if input().strip() != "publish":
        print("not published")
        return 1
    dep = call("POST", f"{base(st['sandbox'])}/deposit/depositions/{st['id']}/actions/publish",
               token(st["sandbox"]))
    st["published"] = True
    st["record"] = dep.get("links", {}).get("record_html") or dep.get("links", {}).get("html")
    st["conceptdoi"] = dep.get("conceptdoi")
    save_state(export, st)
    print("published:", st["record"], "| version DOI", dep.get("doi"), "| concept DOI",
          dep.get("conceptdoi"))
    return 0


def cmd_discard(a) -> int:
    export = Path(a.export)
    st = load_state(export)
    if st.get("published"):
        raise ZenodoError("this deposition is published and cannot be discarded")
    call("DELETE", f"{base(st['sandbox'])}/deposit/depositions/{st['id']}", token(st["sandbox"]))
    (export / STATE).unlink()
    print("draft", st["id"], "deleted")
    return 0


STEPS = {"reserve": cmd_reserve, "upload": cmd_upload, "status": cmd_status,
         "publish": cmd_publish, "discard": cmd_discard}


def main(args) -> int:
    try:
        return STEPS[args.step](args)
    except ZenodoError as e:
        print(f"ZENODO: {e}", file=sys.stderr)
        return 2
