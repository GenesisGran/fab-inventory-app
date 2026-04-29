# FAB Vault: AI-Augmented TCG Inventory System

A high-performance, relational database solution for Flesh and Blood collectors. This project demonstrates how to bridge the gap between messy spreadsheets and rigid mobile apps using a full-stack Python/PostgreSQL architecture.

## 🚀 Live Demo
[Insert Your Streamlit Link Here]

## 🤖 AI-Augmented Engineering (The Workflow)
This project was built using an **AI-augmented development lifecycle**. Rather than writing every line of boilerplate, I acted as the **Technical Architect and Prompt Engineer**, using Google Gemini to:
- **Schema Optimization:** Rapidly iterate on a 6-table relational SQL schema.
- **Query Engineering:** Generate complex PostgreSQL Views to handle server-side data joins.
- **Logic Debugging:** Resolve edge cases in Pandas data transformations, such as null-state handling and string slicing.
- **Outcome:** Reduced development time by 60% while maintaining high standards for relational integrity.

## 🛠️ Tech Stack
- **Frontend:** Streamlit (Python)
- **Database:** Supabase (PostgreSQL)
- **Data Engine:** Pandas (Data Transformation & Aggregation)
- **API:** PostgREST via `httpx`

## 🔍 Features & Data Architecture
The app leverages a specialized **SQL View** that merges transaction data with card metadata to provide a professional-grade dashboard:
- **Card ID Parsing:** Automatically extracts "Set Codes" (e.g., DTD206) from print identifiers.
- **Class & Color Mapping:** Integrates `type_text` and `pitch` values into a readable format with emoji indicators.
- **Relational Integrity:** Unlike Excel, the system uses Foreign Keys to ensure that inventory records are always linked to valid card prints.

## 📊 Why this over Excel?
| Feature | Excel Spreadsheets | FAB Vault |
| :--- | :--- | :--- |
| **Data Integrity** | High risk of typos/broken links | **Strict Foreign Key Constraints** |
| **Scalability** | Slows down at 1,000+ entries | **PostgreSQL Optimized Indexing** |
| **Automation** | Manual color/class entry | **Automated Data Mapping** |

## 🛡️ Security & Technical Debt
To maintain the project as an agile MVP, user credentials are currently stored in plaintext. 
**Roadmap:** The next phase involves implementing **Argon2 password hashing** and transitioning to **JWT session management** to reach production-grade security standards.