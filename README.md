# FAB Vault: AI-Augmented TCG Inventory System

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B.svg)](https://fab-inventory.streamlit.app/)
[![Supabase](https://img.shields.io/badge/Database-Supabase-green.svg)](https://supabase.com/)

**[🚀 View Live Demo](https://fab-inventory.streamlit.app/)**

FAB Vault is a high-performance, relational database solution for Flesh and Blood collectors. It bridges the gap between chaotic spreadsheets and rigid mobile apps by providing a professional-grade dashboard powered by a full-stack Python/PostgreSQL architecture.

## 🤖 AI-Augmented Engineering
This project was developed using a modern **AI-augmented development lifecycle**. As the Technical Architect, I leveraged Google Gemini to accelerate delivery:
* **Schema Optimization:** Rapidly iterated on a 6-table relational SQL schema to ensure 3NF compliance and data integrity.
* **Query Engineering:** Generated complex **PostgreSQL Views** to handle server-side data joins, minimizing client-side latency.
* **Logic Debugging:** Resolved edge cases in Pandas data transformations, specifically regarding null-state handling and card ID parsing.
* **Outcome:** Reduced development time by 60% while maintaining high standards for relational integrity.

## 🛠️ Tech Stack
* **Frontend:** Streamlit (Python)
* **Database:** Supabase (PostgreSQL)
* **Data Engine:** Pandas (Data Transformation & Aggregation)
* **API:** PostgREST via `httpx`

## 🔍 Data Architecture & Features
The app leverages specialized **SQL Views** that merge transaction data with card metadata for real-time reporting:
* **Card ID Parsing:** Automatically extracts "Set Codes" (e.g., DTD206) from print identifiers.
* **Class & Color Mapping:** Integrates `type_text` and `pitch` values into a readable format with emoji indicators.
* **Relational Integrity:** Unlike Excel, the system uses Foreign Keys to ensure inventory records are always linked to valid card prints.

## 📊 Why this over Excel?
| Feature | Excel Spreadsheets | FAB Vault |
| :--- | :--- | :--- |
| **Data Integrity** | High risk of typos/broken links | **Strict Foreign Key Constraints** |
| **Scalability** | Performance degrades >1k rows | **PostgreSQL Optimized Indexing** |
| **Automation** | Manual input for Color/Class | **Automated Metadata Mapping** |

## 🛡️ Roadmap & Security
To maintain agility as an MVP, user credentials are currently handled via a simple management system.
* **Phase 2:** Implement **Argon2 password hashing**.
* **Phase 3:** Transition to **JWT session management** for production-grade security.