#!/usr/bin/env python3
"""Batched GraphQL sweep over open pull requests.

Reads a `gh search prs` JSON dump (repository/number pairs), fetches state,
head, latest review, and the full check-run/status rollup for every PR in
fault-tolerant chunks, and writes one JSON file the patrol loop can diff.

Usage:
    gh search prs --author=YOUR_ACCOUNT --state=open --limit 1000 \
        --json repository,number > /tmp/prs_open.json
    python3 sweep_scan.py /tmp/sweep_out.json [/tmp/prs_open.json]

Requires `gh` authenticated. Aliases are globally unique across chunks and a
failing chunk is bisected, so one malformed entity cannot lose the batch.
"""
import json
import subprocess
import sys

GH = "gh"


def gql(query: str) -> dict:
    r = subprocess.run([GH, "api", "graphql", "-f", f"query={query}"],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:500])
    return json.loads(r.stdout)


def chunk_scan(items, build, size, label):
    results, errors = {}, []

    def run_chunk(chunk):
        q = "{" + " ".join(build(chunk)) + "}"
        try:
            data = gql(q)["data"]
            for key, value in data.items():
                if value is None:
                    errors.append({"key": key, "err": "null (bad repo/num?)"})
                else:
                    results[key] = value
        except Exception as e:  # noqa: BLE001 - bisect and retry smaller
            if len(chunk) > 1:
                mid = len(chunk) // 2
                run_chunk(chunk[:mid])
                run_chunk(chunk[mid:])
            else:
                errors.append({"key": chunk[0]["key"], "err": str(e)[:300]})

    for i in range(0, len(items), size):
        run_chunk(items[i:i + size])
        print(f"  [{label}] {min(i + size, len(items))}/{len(items)} done, "
              f"err={len(errors)}", flush=True)
    return results, errors


SEL = """
state merged closedAt title url
headRefName headRefOid
reviews(last: 1) { nodes { state author { login } submittedAt } }
commits(last: 1) { nodes { commit {
  oid
  statusCheckRollup { contexts(first: 50) { nodes {
    __typename
    ... on StatusContext { context state }
    ... on CheckRun { name conclusion }
  } } }
} } }
"""


def open_sel(alias, it):
    return (f'{alias}: repository(owner: "{it["owner"]}", name: "{it["repo"]}") '
            f'{{ pr: pullRequest(number: {it["num"]}) {{ {SEL} }} }}')


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(1)
    out_path = sys.argv[1]
    in_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/prs_open.json"
    with open(in_path) as f:
        rows = json.load(f)

    items = []
    for i, x in enumerate(rows):
        full = x["repository"]["nameWithOwner"]
        owner, repo = full.split("/", 1)
        items.append({"owner": owner, "repo": repo, "num": x["number"],
                      "idx": i, "key": f"{full}#{x['number']}"})

    results, errors = chunk_scan(
        items, lambda c: [open_sel(f"a{it['idx']}", it) for it in c], 12, "open")

    with open(out_path, "w") as f:
        json.dump({"results": results, "errors": errors}, f)
    print(f"saved {len(results)} results, {len(errors)} errors -> {out_path}")


if __name__ == "__main__":
    main()
