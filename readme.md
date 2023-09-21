# Markdown from Supernote

Python script that uses the Google Drive API to download all supernote '.note' files, and generate Markdown files with
references to such images.

## Notes to myself

Populate the directory with all the markdown and one image per page.

```sh
python main.py
``` 

Sync the contents with the Obsidian vault

```sh
./sync.sh
```

## Outputs

### A note

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

### The index

## Installation

### libs

```
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client supernotelib tqdm
```

### APIs

Configure Google-drive API, and get a credentials.json file.
