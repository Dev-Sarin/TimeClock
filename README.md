# Time Tracker V2 (PySide6)

A lightweight desktop time tracking and pay calculation app built with Python and PySide6.  
Designed for individuals and small teams who want accurate, transparent time tracking without subscriptions or cloud dependencies.

The app supports clock in / clock out, automatic rounding to 6-minute increments (0.1h), wage-based pay calculation, and CSV-based local storage.

---

## Features

- Clock In / Clock Out workflow  
- Live system clock display  
- Date range filtering (for example, last 7 days)  
- Automatic rounding to nearest 6 minutes (0.1 hours) per punch  
- Wage input with real-time pay calculation  
- Detailed table view of punches  
- Dark mode UI (Fusion style)  
- Local CSV storage (no internet required)

---

## Screenshot / UI Overview

- Clean dark UI  
- Punch history table  
- Rounded hours and pay summary  
- Simple, distraction-free design  

---

## Tech Stack

- Python 3.9 or newer  
- PySide6 (Qt for Python)  
- CSV for persistent local storage  
- Cross-platform (Windows, macOS, Linux)

---

## Getting Started

1. Clone the repository
git clone https://github.com/your-username/time-tracker-v2.git
cd time-tracker-v2


2. Create a virtual environment
python -m venv venv

To Activate it:

Windows
venv\Scripts\activate

macOS / Linux
source venv/bin/activate

3. Install dependencies
pip install PySide6

4. Run the app
python time_tracker_V2.py

How Rounding Works
Each punch is rounded individually
Rounds to the nearest 6 minutes
Uses half-up rounding
Matches common payroll rounding standards

Example:
8 minutes rounds to 0.1 hours
14 minutes rounds to 0.2 hours

Data Storage
All punches are stored locally in:

Copy code
time_tracker_data.csv

Format:
csv
Copy code
in_time,out_time
2025-01-01T09:00:00,2025-01-01T17:02:00

No cloud
No tracking
Easy to back up or import elsewhere
Privacy and Offline Use
Fully offline
No telemetry
No external services
Data stays on the local machine

Future Ideas
Export summary reports
Multiple employee profiles
Manual punch editing
Overtime rules
PDF or Excel exports

License
This project is licensed under the GNU General Public License v3.0.
You are free to:
Use the software for any purpose
Study how the software works and modify it
Redistribute copies
Distribute modified versions

Under the condition that:
Source code is disclosed
Modifications are released under the same GPLv3 license
See the LICENSE file for full details.

Author
Sarin Eskandarian
Multi-disciplinary software developer and tool builder
If you are looking for custom desktop tools, automation, or internal business software, feel free to reach out.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.