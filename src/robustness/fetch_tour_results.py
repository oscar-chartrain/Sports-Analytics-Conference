"""Fetch tour-level match results (ATP and WTA, 1968 to 2026) from the pinned archival mirror.

Jeff Sackmann's tennis_atp and tennis_wta (CC BY-NC-SA 4.0) are no longer reachable at
github.com/JeffSackmann, so the files are taken from the archival mirror
github.com/Aneeshers/tennis-sackmann-archive at one commit, and every file is checked against
DATA_MANIFEST.csv (SHA-256 and git blob hash). Files are written to results/tour_results/ (not committed).

    python src/robustness/fetch_tour_results.py          # download missing files, verify, append manifest rows
"""
import os
import csv
import hashlib
import urllib.request

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(REPO_ROOT, 'results', 'tour_results')
MANIFEST = os.path.join(REPO_ROOT, 'DATA_MANIFEST.csv')
COMMIT = '83733587353df8a41f2fd4f516147d5aa83f5a8d'
BASE = f'https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/{COMMIT}'
YEARS = range(1968, 2027)


def blob_sha1(data):
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = list(csv.DictReader(open(MANIFEST, encoding='utf-8')))
    have = {r['file']: r for r in rows}
    new_rows = []
    for tour in ('atp', 'wta'):
        for y in YEARS:
            name = f'{tour}_matches_{y}.csv'
            path = os.path.join(OUT, name)
            url = f'{BASE}/{tour}/{name}'
            if not os.path.exists(path):
                try:
                    data = urllib.request.urlopen(url, timeout=60).read()
                except Exception as e:
                    print(f'missing {name}: {e}')
                    continue
                open(path, 'wb').write(data)
            data = open(path, 'rb').read()
            sha, blob = hashlib.sha256(data).hexdigest(), blob_sha1(data)
            if name in have:
                if have[name]['sha256'] != sha or have[name]['git_blob_sha1'] != blob:
                    raise SystemExit(f'{name}: hash differs from DATA_MANIFEST.csv')
            else:
                new_rows.append(dict(file=name, tour=tour, bytes=len(data), sha256=sha, git_blob_sha1=blob, source_url=url))
    if new_rows:
        with open(MANIFEST, 'a', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=['file', 'tour', 'bytes', 'sha256', 'git_blob_sha1', 'source_url'])
            for r in new_rows:
                w.writerow(r)
        print(f'appended {len(new_rows)} rows to DATA_MANIFEST.csv')
    print(f'{len(os.listdir(OUT))} files in {OUT}; all match the manifest')


if __name__ == '__main__':
    main()
