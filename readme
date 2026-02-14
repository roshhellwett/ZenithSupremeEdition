# 🚀 Zenith Supreme Edition 

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Asyncpg-blue?style=for-the-badge&logo=postgresql)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red?style=for-the-badge)
![Telegram API](https://img.shields.io/badge/Telegram_Bot_API-v20+-blue?style=for-the-badge&logo=telegram)
![License](https://img.shields.io/badge/License-Open_Source-green?style=for-the-badge)

**Zenith Supreme Edition** is an enterprise-grade, highly scalable SaaS (Software as a Service) Telegram Group Moderation engine. Built on a multi-tenant microservices architecture, it empowers group administrators to protect their communities from spam raids, abuse, and hostile takeovers through a frictionless, zero-typing setup interface.

## ✨ Key Features

* **🛡️ 24-Hour Anti-Raid Shield:** Automatically tracks when users join and instantly deletes any media, stickers, or links they attempt to send during their first 24 hours.
* **🧠 "Zero-Typing" Deep Link Setup:** Administrators configure their group settings entirely through private DMs via secure inline buttons—no more copying hidden Group IDs or typing complex commands.
* **⚡ High-Performance Regex & Caching:** Utilizes compiled global regex and `TTLCache` (Time-To-Live) LRU caching to eliminate N+1 database queries and prevent RAM exhaustion under heavy raid loads.
* **🚨 Owner Alert System:** When a rule is violated, Zenith handles the threat publicly but silently DMs the group owner a detailed incident report.
* **👻 Self-Healing Edge Case Management:** Automatically migrates IDs when a group upgrades to a Supergroup, handles anonymous admin broadcasts, bypasses false bans on photo albums, and elegantly shuts down if kicked or blocked.
* **🎭 Smooth Vanishing Animations:** Public warnings are given a 5-second lifespan before automatically deleting themselves to keep the group chat pristine.

[Image of a modern Telegram bot dashboard UI]

## 🏗️ Architecture & Tech Stack

Zenith is built for deployment on modern cloud platforms (like Railway, Render, or AWS) and relies on:
* **Language:** Python 3.11/3.12 (Strictly asyncio-driven)
* **Database:** PostgreSQL (via `asyncpg` for non-blocking I/O)
* **ORM:** SQLAlchemy 2.0 (with connection pooling)
* **Framework:** `python-telegram-bot` v20+

### The Multi-Tenant Container Model
Instead of spinning up physical databases per group, Zenith uses a logical Row-Level Isolation pattern (`zenith_group_settings`). The bot remains completely dormant in a group until the owner successfully authenticates and activates their specific "container" via the DM dashboard.

---

## ⚙️ Installation & Deployment

### 1. Prerequisites
* Python 3.11 or higher
* A PostgreSQL Database URL
* A Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### 2. Local Setup
Clone the repository and move into the directory:
```bash
git clone [https://github.com/yourusername/ZenithSupremeEdition.git](https://github.com/yourusername/ZenithSupremeEdition.git)
cd ZenithSupremeEdition
