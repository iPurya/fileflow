"""Download individual URLs or a batch using a limited thread pool."""

import re
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.client import HTTPException
from urllib.error import HTTPError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

from features.common import unique_path, validate_filename


def download_file(url, folder):
    address = urlsplit(url)
    if address.scheme not in {"http", "https"} or not address.hostname:
        raise ValueError("Only HTTP and HTTPS URLs are supported")

    name = unquote(address.path.rsplit("/", 1)[-1]) or "download"
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).rstrip(". ")
    try:
        validate_filename(name)
    except ValueError:
        name = "download"

    request = Request(url, headers={"User-Agent": "FileFlow/0.1"})
    try:
        response = urlopen(request, timeout=30)
    except HTTPError as error:
        error.close()
        raise
    with response:
        # Exclusive creation prevents simultaneous downloads from overwriting files.
        while True:
            destination = unique_path(folder / name)
            try:
                output = destination.open("xb")
                break
            except FileExistsError:
                continue
        try:
            with output:
                shutil.copyfileobj(response, output)
            expected = response.headers.get("Content-Length")
            if expected and destination.stat().st_size != int(expected):
                raise OSError("The download ended before the full file arrived")
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
    return destination


def run(args):
    urls = list(args.urls)
    if args.from_file:
        lines = args.from_file.read_text(encoding="utf-8-sig").splitlines()
        urls.extend(
            line.strip()
            for line in lines
            if line.strip() and not line.strip().startswith("#")
        )
    if not urls:
        raise ValueError("Provide a URL or a non-empty --from-file text file")

    folder = args.output.expanduser().resolve()
    folder.mkdir(parents=True, exist_ok=True)
    failures = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs = {pool.submit(download_file, url, folder): url for url in urls}
        try:
            for job in as_completed(jobs):
                try:
                    print(f"Downloaded: {job.result()}")
                except (OSError, ValueError, HTTPException) as error:
                    failures += 1
                    print(f"Failed: {jobs[job]} ({error})", file=sys.stderr)
        except KeyboardInterrupt:
            for job in jobs:
                job.cancel()
            raise
    print(f"Downloaded {len(urls) - failures} file(s); failed {failures}.")
    return 1 if failures else 0
