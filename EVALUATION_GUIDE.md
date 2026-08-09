# Ledger — Hackathon Evaluation & Demo Guide

> **Sairam Hackathon-2026 Submission**  
> **Team Name**: Blue Silver Avengers  
> **Project Title**: Ledger — Conversational Database Agent  
> **Submission Date**: August 12, 2026  

---

## 🎯 What is Ledger? (The Elevator Pitch)

For many business managers, decision-makers, and educators, database systems are like a black box. To find out something simple—like *"Who are our top customers?"*—they have to wait for a database administrator to write complex code (SQL) and compile a report.

**Ledger solves this barrier.** It acts as an **intelligent, conversational data assistant**. You can ask it questions in plain English (or speak to it using your microphone), and it will automatically:
1. Look at your database layout.
2. Ask the database for the correct data securely.
3. Draw beautiful, interactive charts (Bar, Line, Pie, or Scatter graphs).
4. Outline relationships between datasets as diagrams.
5. Explain the data findings in simple words.

---

## 🚀 The 3-Minute Demo Script (For Judges & Staff)

Follow these steps to experience the full capabilities of Ledger. No technical setup or code-writing is required.

### Step 1: Open the Application
* Open `http://localhost:5173` in your web browser. You will see a dark, modern dashboard with a chat input at the bottom.

---

### Step 2: Open the Database Explorer (Left Sidebar)
* Click the **Schema Explorer** button in the top header.
* A panel will slide in from the left listing four tables: `customers`, `orders`, `order_items`, and `products`.
* Click on `customers` to expand it. You will see the columns (e.g., `name`, `email`, `region`). 
* **Action**: Click the copy icon next to any table name or column to copy it instantly, or click the `+` icon to insert it directly into your chat box.

---

### Step 3: Ask a Question & Get a Chart
* Click on the suggestion button: **"Show me the top 5 products by revenue this quarter"** (or type it in the box and click **Send**).
* **What to expect**: 
  1. Ledger will display a checklist showing it is querying the database.
  2. A vibrant bar chart will appear on the screen.
  3. Hover your mouse over the bars to see real-time price totals.
  4. Click **Export CSV** to download the query results as a spreadsheet, or click **Export PNG** to save the graph to your desktop.
  5. A paragraph below the chart will explain the sales trends.

---

### Step 4: Generate a Database Map (ER Diagram)
* In the chat input, type: **"Draw me the ER diagram for this database"** and press Enter.
* **What to expect**: Ledger will generate an interactive relationship tree showing how your tables link together, followed by a non-technical breakdown of the connections.

---

### Step 5: Speak to Your Database (Voice Mode)
* Click the **Microphone** icon next to the send button.
* Grant microphone permissions if prompted. 
* Speak clearly: *"Which region has the most customers?"*
* **What to expect**: Ledger will translate your voice into text, place it in the input field, run the query, and provide the answer.

---

## 🔒 Security Explained (Simple Analogies)

A common concern with AI database assistants is: *"What if the AI accidentally deletes or leaks data?"* Ledger is built with a dual-layer security shield to make this impossible:

1. **The Read-Only Shield (The Vault)**  
   * **Analogy**: Like a bank customer looking at a bank balance statement behind bulletproof glass, they can see the balance, but they can't reach in and take the cash.
   * **How it works**: Ledger connects to the database using a strict `agent_readonly` user account. It can only execute `SELECT` (read) commands. It is physically blocked by the database from performing write, update, delete, or schema modification operations.

2. **The AST Gatekeeper (The Security Guard)**  
   * **Analogy**: Like a security guard at an entrance who inspects every bag. If they see any weapon (destructive query words like `DROP`, `DELETE`, `UPDATE`, or `INSERT`), they block the visitor from entering.
   * **How it works**: The backend inspects the grammatical structure of every SQL query before letting it reach the database. If it detects any non-read commands, it stops execution immediately and alerts the user.

3. **The Data Safety Clamp**  
   * **How it works**: Ledger automatically limits query results to a maximum of 100 rows to prevent the system from slowing down or crashing when handling massive datasets.

---

## 🛠️ Technology Stack Overview

For the technically curious, here is the structure of the system:
* **Frontend (Visual Interface)**: Built using **React** and **Vite** for fast, responsive loading. Uses **Recharts** for graphing and **Mermaid.js** for rendering diagrams.
* **Backend (Broker Server)**: Built using **FastAPI** (Python), managing tool-calling paths and executing query validations.
* **AI Engine (The Brain)**: Leverages **Google Gemini 3.1 Flash-Lite**, optimizing cost, execution speed, and database logic schema comprehension.
