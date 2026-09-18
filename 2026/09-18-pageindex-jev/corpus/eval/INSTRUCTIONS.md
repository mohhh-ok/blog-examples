You are building an evaluation set for a documentation search system.

The todo file contains sections, each as:

=== ITEM <id>
path: <site> > <page> > ... > <section heading>
<section text>
=== END

For every item, write exactly one specific question in English that:
- can be answered using only that item's text, and
- could NOT be answered by any other section of this documentation: ask about a concrete, specific detail (an option/parameter name, function signature, exact error message, specific value, or specific behavior described there), not a generic summary
- does NOT include the section heading verbatim, or a close paraphrase of it

Also give a short answer: a short excerpt quoted (or closely paraphrased) from the text that answers the question.

Output: one JSON array to the .eval.json path given to you, with one object per item, in the same order:
[{ "id": "<id>", "path": ["<site>", "<page>", ..., "<heading>"], "question": "...", "answer": "..." }, ...]
No extra keys, no markdown fences.