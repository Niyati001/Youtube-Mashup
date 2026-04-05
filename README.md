# Mashup Assignment

## Requirements
Install dependencies:
```
pip install -r requirements.txt
```

---

## Program 1 – Command Line Mashup

### Usage
```
python mashup.py "<SingerName>" <NumberOfVideos> <AudioDuration> <OutputFileName>
```

### Example
```
python mashup.py "Sharry Maan" 15 25 output.mp3
```

### Rules
- `NumberOfVideos` must be **> 10**
- `AudioDuration` must be **> 20** (seconds)
- `OutputFileName` must end with `.mp3`

---

## Program 2 – Web App

### Setup Email (Gmail)
1. Enable 2-Step Verification on your Google account.
2. Generate an **App Password**: Google Account → Security → App Passwords.
3. Set environment variables before running:

**Windows:**
```
set SMTP_USER=your_email@gmail.com
set SMTP_PASS=your_app_password
```

**Mac/Linux:**
```
export SMTP_USER=your_email@gmail.com
export SMTP_PASS=your_app_password
```

### Run
```
python app.py
```
Visit: [http://localhost:5000](http://localhost:5000)

### How It Works
1. User fills in Singer Name, # of Videos, Duration, Email.
2. Server validates inputs.
3. Background thread downloads videos, converts to audio, cuts clips, merges them.
4. Result is zipped and emailed to the user.

---

## File Structure
```
mashup.py          ← Program 1 (CLI)
app.py             ← Program 2 (Flask web app)
requirements.txt   ← Python dependencies
README.md          ← This file
```
