# Rosterwire

Rosterwire is a modern web application for viewing recent NBA transactions and exploring full rosters of players by team. It features clean navigation, real-time data from the NBA API, and a user-friendly interface with player stats and value ratings.

---

## 🌟 Features

- 🏀 **NBA Roster Viewer** — Explore team rosters with season and career stats.
- 🔄 **Transaction Feed** — View latest NBA trades and signings.
- ⭐ **Player Rating System** — Visual star ratings (0–5) based on last season performance.
---

## ⚙️ Technologies Used

- **Frontend**: Next.js 13+, React, Tailwind CSS
- **Backend**: Flask (Python)
- **Data**: `nba_api` (Swar/NBA_API)
- **Design**: Responsive with professional red/white/blue/black theme

---

## 🧰 Setup Instructions

### 1. 📦 Node/NPM Frontend Setup
Clone the repository:<br>
git clone https://github.com/Mebben11/Rosterwire2.0.git<br>
cd {Download Location}/Rosterwire2.<br>
<br>
Navigate to frontend:<br>
cd {Rosterwire2.0 Location}
<br>
Install dependencies:<br>
npm install<br>
<br>
###📦 2. Frontend Setup (Next.js)<br>
Start the frontend:<br>
npm run dev<br>
<br>
This will start the app at:<br>
http://localhost:3000<br>
<br>
###🐍 3. Backend Setup (Flask API) - new cmd (recommended)<br>
Navigate to the Flask API directory:<br>
cd {Download Location}/Rosterwire2.0/nba_server<br>
<br>
Create a virtual environment:<br>
python -m venv venv<br>
source venv/bin/activate  # On Windows: venv\Scripts\activate<br>
<br>
Install dependencies:<br>
pip install -r requirements.txt<br>
Start the Flask server:<br>
python app.py<br>
This will start the backend server at:<br>
http://localhost:5000<br>
<br>
Ensure that CORS is properly configured to allow communication between frontend and backend.<br>
<br>
Root/
├── .next/                        # Next.js build files (⚠️ not in repo)<br>
├── App.js                        # Main React component (optional)<br>
├── index.js                      # Entry point<br>
├── package.json                  # Frontend dependencies and scripts<br>
│<br>
├── components/                   # UI Components<br>
│   ├── PlayersTable.js<br>
│   ├── Sidebar.js<br>
│   ├── StarRating.js<br>
│   └── TransactionsTable.js<br>
│<br>
├── nba_server/                   # Flask backend<br>
│   └── app.py                    # API route and player logic<br>
│   └── (venv/, __pycache__/ etc - ⚠️ not in repo)<br>
│<br>
├── node_modules/                 # Installed packages (⚠️ not in repo)<br>
│<br>
├── pages/                        # Next.js page routes<br>
│   ├── _app.js                   # Layout and theme provider<br>
│   ├── index.js                  # Home (Rosters view)<br>
│   ├── script.js                 # Data handlers / utils<br>
│   └── transactions.js          # NBA transaction page<br>
│<br>
├── rosterwire-frontend/         # Working frontend directory (⚠️ not in repo)<br>
│<br>
└── styles/                       # CSS modules<br>
    ├── globals.css<br>
    ├── PlayersTable.module.css<br>
    ├── Sidebar.module.css<br>
    ├── StarRating.module.css<br>
    └── TransactionsTable.module.css<br>
<br>
###🚀 How to Start the App<br>
cd {Download Location}/Rosterwire2.0/nba_server<br>
source venv/scripts/activate<br>
python app.py<br>
<br>
(additional cmd) cd {Download Location}/Rosterwire2.0r<br>
npm install<br>
npm run dev<br>
<br>
Then visit:<br>
📍 http://localhost:3000<br>
<br>
🔚 Notes<br>
API filters out preseason and summer league games.<br>
Players with < 5 GP (Games Played) are excluded.<br>
Project fetches from the nba_api.stats.endpoints.commonplayerinfo and others.<br>
<br>
📫 Contact<br>
Created by Michael Ebben<br>
Contact for questions or feature suggestions. - Mikeyebben@gmail.com<br>
