# Example assets

Fictional starting points for the private files the workflows read. Nothing here is used at run time.

| File | Copy to | Read by |
|---|---|---|
| `letter_skeleton.tex` | `assets/letter_skeleton.tex` | WF3, path stored in `applicants.skeleton_file` |
| `email_sample.txt` | `assets/email_sample.txt` | WF3, path stored in `applicants.email_sample_file` |

Replace every name, address and paragraph with your own before use. The `assets/` folder is ignored by Git; keep your real documents there, together with your CV and `declaration.pdf`.

The email sample holds the body only. WF3 strips a leading `Madame, Monsieur,` and WF4 adds the greeting, `Cordialement,` and the sender name.

WF3 replaces only the first `<<RECIPIENT>>` and the first `<<DATE>>` in the template. Keep exactly one of each, and do not repeat them in comments.
