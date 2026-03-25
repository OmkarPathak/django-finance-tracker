# TrackMyRupee
## The Privacy-First Personal Finance Dashboard for Professionals

**TrackMyRupee** is a premium, privacy-focused personal finance dashboard designed for individuals who want to take full control of their financial story — without compromising their data.

Unlike traditional finance apps, TrackMyRupee **does not** read your SMS, **does not** require bank logins, and **never** sells your data. It is built on the principle of *manual precision*: you stay in the driver's seat of your wealth.

**[Try the Live App](https://trackmyrupee.com)** | **[View Demo](https://trackmyrupee.com/demo/)** | **[Star on GitHub](https://github.com/OmkarPathak/trackmyrupee)**

<div align="center">

![Stars](https://img.shields.io/github/stars/omkarpathak/trackmyrupee?labelColor=F0F0E8&style=for-the-badge&color=1D9E75)
![Forks](https://img.shields.io/github/forks/omkarpathak/trackmyrupee?labelColor=F0F0E8&style=for-the-badge&color=1D9E75)
![Django](https://img.shields.io/badge/Django-4.x-green?labelColor=F0F0E8&style=for-the-badge&color=1D9E75)
![License](https://img.shields.io/badge/license-MIT-blue?labelColor=F0F0E8&style=for-the-badge&color=1D9E75)
![Privacy First](https://img.shields.io/badge/Privacy-First-brightgreen?labelColor=F0F0E8&style=for-the-badge&color=1D9E75)

</div>

---

## 💎 Why TrackMyRupee?

Stop being the product. Most "free" finance apps profit by selling your spending habits. TrackMyRupee is built differently:

- **🔒 Zero Surveillance**: No SMS reading. No bank scraping. Period.
- **📈 Comprehensive Net Worth**: Track Cash, Bank Accounts, and Assets in one unified view.
- **🎯 Goal-Slaying Engine**: Visual savings goals with progress tracking and celebratory milestones.
- **🌍 Global Ready**: Multi-currency support with real-time conversion and multi-language interfaces (English, Hindi, Marathi).
- **🛡️ Data Sovereignty**: Export your entire history anytime. Delete your account and all data with one click.

![Budget Dashboard – TrackMyRupee](static/img/desktop.png)

---

## Features

### 💰 Wealth Management
*   **Account Ledger**: Detailed transaction history for every bank account and cash wallet.
*   **Internal Transfers**: Easily move money between accounts with balanced reconciliations.
*   **Net Worth Tracking**: Watch your total wealth grow with automated account balance aggregation.

### 📉 Smart Tracking
*   **Manual & Bulk Entry**: Add single expenses or import months of data via Excel.
*   **Recurring Transactions**: Never miss a rent payment or SIP with smart reminders and automated scheduling.
*   **AI Category Prediction**: Intelligent suggestions for your expenses to speed up manual logging.

### 🎯 Savings Goals
*   **Visual Progress**: Beautiful progress bars and milestone badges (Started, 25%, 50%, 75%).
*   **Gamified Success**: Confetti celebrations when you reach your targets!
*   **Auto-Refunding**: Delete a goal? All contributions are automatically "refunded" back to their source accounts.

### 📊 Insights & Analytics
*   **Visual Dashboards**: Deep dives into your spending by category and account.
*   **Month-over-Month Analysis**: Compare your financial habits over time.
*   **Year in Review**: A wrap-up of your annual spending story.
*   **Automated Reports**: Get monthly financial summaries delivered straight to your inbox.

---

## 🚀 Quick Start

### Self-Hosted (Docker)
Run your own private instance in seconds:
```bash
git clone https://github.com/OmkarPathak/trackmyrupee
cd trackmyrupee
docker-compose up
```
Visit: `http://localhost:8000`

### Manual Setup (Django)
```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations & setup
python manage.py migrate
python manage.py createsuperuser

# Start the dashboard
python manage.py runserver
```

---

## 🛠️ Built With
*   **Backend**: Python 3.x, Django 4.2+
*   **Database**: PostgreSQL / SQLite
*   **Frontend**: Vanilla JS, Bootstrap 5, Chart.js
*   **DevOps**: Docker, GitHub Actions, Sentry

---

## 📬 Contact & Support
TrackMyRupee is an open-source project by **[Omkar Pathak](https://omkarpathak.in)**.
Found a bug? Have a feature request? Feel free to **[Open an Issue](https://github.com/OmkarPathak/trackmyrupee/issues)**.

---

## 📜 License
Licensed under the **MIT License**. Your money, your data, your code.
