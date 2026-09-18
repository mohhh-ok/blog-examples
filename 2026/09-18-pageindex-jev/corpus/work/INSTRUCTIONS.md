# Manifest writing task

For each input file `corpus/work/<site>/<n>.md` assigned to you, write `corpus/work/<site>/<n>.json` (same directory, same basename).

The input is one documentation page: a `# title` line, the page's intro text, then zero or more `[[SECTION i: heading]]` blocks (i starts at 0).

Output JSON shape (strict, no extra keys, no markdown fences):

{
  "page": "<page manifest>",
  "sections": [ { "index": 0, "manifest": "<section manifest>" }, ... ]
}

`sections` must have exactly one entry per `[[SECTION i]]` marker in the input, with the matching index. If the page has no markers, `sections` is `[]`.

## What a manifest is

You index technical documentation for a retrieval router. The router reads only your manifests to decide whether the answer to a user's question is inside a page or section, so a manifest must be an exhaustive inventory, not a prose summary. Prefer coverage over brevity; never add anything that is not in the text.

For the page as a whole and for each [[SECTION i: heading]] block, write a manifest as terse bullet lines covering:
- topics and tasks covered
- every named identifier: functions, methods, options, config keys, CLI flags, environment variables, types, error messages (verbatim)
- concrete values: defaults, limits, versions, numbers, file paths
- caveats, platform/runtime conditions, "not supported" statements
- 3 to 6 questions this text answers, phrased as a user would ask

Page manifest: 80-200 words. Section manifest: 60-200 words depending on the section's size.

Write bullet lines separated by newlines inside the JSON string (escape as \n). Process every assigned file. Do not skip files, do not summarize the whole site, do not modify any other file.
