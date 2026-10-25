# Local research-brief renderer

`render_research_brief.py` renders a caller-supplied scene to an editable 16:9 PPTX and a PDF generated from the same scene. It does not start experiments or query any scientific model. All output, image and font paths are checked against the supplied workspace root.

Supported primitives: editable rectangles, ellipses, chevrons, lines, text and embedded chart images. Text is wrapped with the local TrueType font metrics and checked against its box height. The PDF embeds the supplied Chinese font; PPTX specifies Microsoft YaHei for Chinese/Latin text. Font substitutions in a particular Office installation are not tested by this utility.

```python
from render_research_brief import render
render(scene, pptx_path, pdf_path, regular_font, bold_font,
       workspace_root=project_root)
```

The PDF is a same-layout preview, **not a LibreOffice/Microsoft Office conversion**. A presentation should still be inspected as a rendered PDF and structurally reopened with `python-pptx`. The local presentation workflow also checks glyph coverage, native shape bounds, PDF text bounds, source SHA, and DOCX readability.

Dependencies are recorded in `configs/requirements-presentation-20261025.lock.txt`. Only python-pptx, python-docx, reportlab and PyMuPDF plus their necessary dependencies were added; the earlier environment lock is retained for comparison. Existing numerical packages were not changed.

Chinese PDF font source: Google's Noto Sans SC, SIL Open Font License, https://github.com/google/fonts/tree/main/ofl/notosanssc . Font assets remain under the project-local ignored data directory, with actual download URL, SHA and license. No global font installation is required.

Internal scene content, slides, speech, charts and previews are stored in the ignored local deliverables directory. They must not be automatically published to the public repository. The public source manifest lists only existing public scientific reports/metric sources and their hashes, without slide text or internal speaker notes.
