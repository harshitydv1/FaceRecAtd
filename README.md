# Food Mess Management & Attendance System

A production-ready, Streamlit-based food mess management system powered by AI face recognition.

---

## Quick Start (Local Setup)

### 1. Prerequisites (macOS)
```bash
# Install cmake (required by face_recognition/dlib)
brew install cmake
```

### 2. Clone / navigate to the project
```bash
cd /Users/harshit/Desktop/FaceRecAtd
```

### 3. Create & activate virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```
 
### 5. Run the app
```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) (or whichever port Streamlit specifies) in your browser.

---

## Project Structure

```
FaceRecAtd/
├── app.py                          # Unified Dashboard (Scanner, Registration, Records)
├── core/
│   ├── database.py                 # SQLite Database Management
│   └── face_engine.py              # Face detection and encoding logic
├── utils/
│   └── helpers.py                  # Utility functions
├── data/
│   └── attendance.db               # SQLite DB (auto-generated)
└── requirements.txt                # Python dependencies
```

---

## Features

- **Food Program Management**: Easily track which students/staff are enrolled in the Food Mess program.
- **Meal Phases**: System automatically tracks Breakfast, Lunch, and Dinner based on the time of day.
- **Smart Face Scanning**: Input methods include Webcam Snapshot, File Upload, and an optimized Live CCTV Scanner that scans continuously and logs attendees instantly in a timeline.
- **Records & Reporting**: View daily logs, filter by user/department, and export everything directly to a CSV file.
- **Database Control**: Built-in SQLite database with one-click full data wipes for clearing history between sessions.
- **Clean Interface**: Beautiful, dark-mode Streamlit dashboard with no clutter.




