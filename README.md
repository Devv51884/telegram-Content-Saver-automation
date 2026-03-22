# Code Devil Restricted Saver Structured V3

V3 adds basic admin controls on top of the structured V2 bot.

## Features
- Hinglish UI
- Force subscribe
- Settings panel
- Admin basics:
  - /stats
  - /users
  - /ban user_id
  - /unban user_id
  - /broadcast message

## Setup
1. Create `.env` from `.env.example`
2. Fill values
3. Run:
   ```bash
   python -m venv venv
   venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python main.py
   ```

## Notes
- `OWNER_ID` is required for admin commands.
- `ADMIN_IDS` can be comma-separated extra admins.
- Bot should be admin in your force-sub channel.
