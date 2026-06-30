# Arabic Transliteration

`arabic_transliteration.py` is a self-contained Python script for transliterating fully vocalized Arabic text into two Indonesian-oriented Latin forms:

- `T_rev`: a compact reversible transliteration intended to encode Arabic in a typeable Latin form and decode it back to normalized Arabic.
- `T_read`: a pronunciation-oriented transliteration intended for Indonesian readers.

The script uses only the Python standard library.

## Requirements

- Python 3.9 or newer
- A terminal that can accept UTF-8 Arabic input

On Windows, PowerShell or Windows Terminal is recommended.

If Arabic text appears garbled in a legacy console, run Python in UTF-8 mode:

```bash
python -X utf8 arabic_transliteration.py
```

## Running the Script

From the repository directory, run:

```bash
python arabic_transliteration.py
```

The default interactive menu shows:

```text
Arabic Transliteration
1. Decode Latin transliteration to Arabic and T_read
2. Encode Arabic into Latin
Select option [1-2]:
```

### Option 1: Decode T_rev

Use this when you already have reversible Latin transliteration and want Arabic plus readable pronunciation.

Example input:

```text
bis.mi Alllah
```

Example output:

```text
Arabic: بِسْمِ اللَّه
T_read: bismillah
```

### Option 2: Encode Arabic

Use this when you have Arabic text and want both transliteration forms.

Example input:

```text
بِسْمِ اللَّهِ
```

Example output:

```text
T_rev : bis.mi Alllahi
T_read: bismillah
T_REV ROUND-TRIP: PASS
```

The round-trip line reports whether the produced `T_rev` can be decoded back into the normalized Arabic input.

## Using as a Python Module

You can also import the script from another Python file.

```python
import arabic_transliteration as tr

arabic = "بِسْمِ اللَّهِ"

print(tr.to_t_rev(arabic))
# bis.mi Alllahi

print(tr.to_t_read(arabic))
# bismillah

print(tr.from_t_rev("bis.mi Alllahi"))
# بِسْمِ اللَّهِ

result = tr.transliterate(arabic)
print(result.t_rev)
print(result.t_read)
```

The public functions are:

- `normalize_arabic(text)`: normalizes Arabic text into the internal canonical form.
- `to_t_rev(arabic)`: converts Arabic into reversible `T_rev`.
- `from_t_rev(t_rev)`: decodes `T_rev` back into Arabic.
- `to_t_read(arabic)`: converts Arabic into readable Indonesian-oriented Latin.
- `transliterate(arabic)`: returns both `T_rev` and `T_read` in one result object.

## Important Notes

This program is designed for fully vocalized Arabic. Undiacritized Arabic can still be processed in some cases, but the system is intended around Arabic text that includes vowel marks.

`T_rev` is the reversible form. It is stricter than ordinary readable Latin spelling, because every token must preserve enough information to reconstruct Arabic.

`T_read` is not reversible. It applies pronunciation-oriented rules such as readable long vowels, connected-reading behavior, and sentence-final waqf.

## Configuration Flags

The main configuration flags are near the top of `arabic_transliteration.py`:

```python
ALLOW_CONVENTIONAL_T_REV_USER_INPUT = True
SHOW_TESTS_IN_UI = False
VISUAL_RTL_CONSOLE_FALLBACK = sys.platform == "win32"
```

### `ALLOW_CONVENTIONAL_T_REV_USER_INPUT`

When enabled, `from_t_rev()` accepts whole-word readable aliases such as `Allah`, `Allahi`, `Allahu`, and `Allaha` and decodes them as the canonical reversible spelling with three `l`s.

Canonical `T_rev` still uses:

```text
Alllah
Alllahi
Alllahu
Alllaha
```

### `SHOW_TESTS_IN_UI`

Leave this as `False` for a simple exported repository containing only `arabic_transliteration.py`.

If changed to `True`, the interactive menu shows option `3` for running tests. This is intended for a development copy that includes the test files.

### `VISUAL_RTL_CONSOLE_FALLBACK`

On Windows, some terminals display Arabic from left to right. This flag visually reorders Arabic console output so it appears right-to-left in those terminals. If your terminal already displays Arabic correctly, set it to `False`.

No installation step is required.
