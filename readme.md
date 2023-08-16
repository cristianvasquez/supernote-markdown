# Markdown from Supernote

- Downloads supernote-notes from google-drive, puts them in temp.
- Generates SVGs for all the pages of such notes.
- Generates markdown for all notes, pointing to the notes.

## Run

```
python main.py
```

### Output

A directory 'supenote', with one markdown files for the notes. All images in a `images` dir.

Example output: 

```markdown
---
alias: Generative AI.note
file_size: 892.49KB
last_modified: 2023-07-25T23:44:57.496Z
---

# Generative AI.note

## 1

![[1aOJdvWZ9sRyH_bSBeu8XECrf4rlFQ3de_0.svg]]

## 2

![[1aOJdvWZ9sRyH_bSBeu8XECrf4rlFQ3de_1.svg]]


```

## Installation

### libs

```
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client supernotelib tqdm
```

### APIs

Configure Google-drive API, get a credentials.json file.
