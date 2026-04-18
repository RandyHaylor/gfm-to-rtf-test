# DOCX Implementation Tasks

## Phase 1: Text Placeholder System
- [x] Create `_DOCX_TEXT_PLACEHOLDER_STASH` dict and `docx_stash_user_text()` helper
- [x] Create `docx_restore_all_stashed_text()` that replaces all placeholders with XML-escaped text
- [x] Create `docx_reset_text_placeholder_stash()` to clear state between conversions
- [x] Test: stash and restore a string with `&`, `<`, `>`, `"` characters — passed

## Phase 2: Update Inline Rules to Use Placeholders
- [x] bold/italic/strikethrough — stash the captured text, emit XML structure with placeholder
- [x] inline code — stash the code content
- [x] subscript/superscript/underline — stash the text
- [x] Test: run inline rules in docx mode, verify output has placeholders not raw text

## Phase 3: Links and Mentions
- [x] md_link — stash link display text, emit hyperlink XML with placeholder
- [x] bare_url — stash URL text
- [x] mention — stash @username text
- [x] issue_ref — stash #number text
- [x] footnote_ref — stash footnote ID text
- [x] Test: verify hyperlink relationship IDs are still collected correctly

## Phase 4: Block Rules
- [x] paragraph — collect inline output, wrap in `<w:p>`, call restore at block level
- [x] heading — emit heading style XML, stash heading text
- [x] blockquote/alerts — stash quote text content
- [x] list items — stash item text content
- [x] table cells — stash cell content
- [x] code blocks — stash each line of code
- [x] footnote section — stash footnote text
- [x] horizontal rule — no text, just XML structure
- [x] Test: generate DOCX, validate XML with validator script

## Phase 5: Document Assembly
- [x] Wire `_docx_restore_text()` into final XML before zipping
- [x] Build document.xml.rels with hyperlink relationships
- [x] Build styles.xml with heading styles
- [x] Zip into .docx
- [x] Test: open in Word/LibreOffice, verify content renders  *(automated XML validation passes; user visual check in LibreOffice is separate)*

## Phase 6: Verify RTF Unchanged
- [x] Diff RTF output against known-good to confirm no regressions  *(byte-identical to pre-Phase-2 pinned copy)*
