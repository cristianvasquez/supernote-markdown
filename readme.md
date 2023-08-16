# Markdown from Supernote

- Downloads supernote-notes from Google Drive, puts them in temp.
- Generates markdown and images for each note.

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

Configure Google-drive API, and get a credentials.json file.

## Run

```
python main.py
```
