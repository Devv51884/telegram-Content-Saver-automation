# Code Devil Restricted Saver Structured V4

V4 adds advanced settings pages and automatic indexing commands on top of the working V3 bot.

## New in V4
- Advanced settings sub-pages
- Thumbnail save/remove
- Caption set/remove
- Prefix / suffix helpers
- Metadata submenu
- Upload mode fixed to Telegram
- Admin indexing commands:
  - /index_id
  - /stop_index
  - /index_stats

## Notes
- /index_id enables auto-indexing for the admin who runs it.
- Every new private message/media sent while index mode is on gets stored in `data/index_store.json`.
- Use /stop_index to stop auto indexing.

## Setup
```bash
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```
