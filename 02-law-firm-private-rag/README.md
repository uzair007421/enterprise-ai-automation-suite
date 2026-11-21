# ⚖️ Project 02: Private On-Premise Legal RAG Chatbot

> **Commercial Brief:**  
> *"Our lawyers waste hours searching old case files (PDFs, Word). Build a chatbot that answers only from our documents, shows the exact source page, and says 'I don’t know' when it isn’t sure. No client data may leave our server."*

---

## 🔒 Security & Privacy Highlights
* **Zero External Cloud Leakage:** All chunking, indexing, and vector space similarity computations execute strictly within the local/on-premise server environment.
* **Strict Hallucination Control:** If semantic confidence falls below the strict evidence threshold, the engine executes a hard refusal: *"I don't know based on the provided law firm documents. This topic is not covered in our internal case archives."*
* **Page-Level Granular Citations:** Every retrieved fact is accompanied by the exact PDF/document title, practice area, page number, and clause excerpt.

---

## 🏗️ Architecture & Search Pipeline

```
[ Law Firm Case Files: PDFs / Word / Contracts ]
                     │
                     ▼
  [ Semantic Chunking Engine (Document + Page Metadata) ]
                     │
                     ▼
  [ Local Vector DB & Inverted TF-IDF/BM25 Index ]
                     │
                     ▼
  [ Cosine Similarity Retrieval Top-K Ranking ]
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
  [ Score >= Threshold ]  [ Score < Threshold ]
         │                       │
         ▼                       ▼
 [ Grounded Answer +     [ STRICT REFUSAL GATE ]
  Exact Page Citation ]  "I don't know based on internal docs"
```

---

## ⚡ How to Run Live Interactive Demo

Zero external pip dependencies required. Works natively with Python 3:

```bash
cd 02-law-firm-private-rag
python run_demo.py
```
Open your browser at: **`http://localhost:8002`**

---

## 🎥 60-Second Fiverr Video Recording Script
1. **(0:00 - 0:15) The Problem:**  
   *"Law firms lose thousands of billable hours digging through hundreds of old case PDFs. Commercial cloud AI tools risk violating attorney-client privilege. Here is our private, air-gapped legal RAG engine."*
2. **(0:15 - 0:35) The Query & Exact Page Citations:**  
   Click the **Antitrust Settlement** or **Non-Compete Precedent** button.  
   Show how within 100 milliseconds, it pulls the exact answer and displays:  
   *`Source: Apex_vs_Meridian_Antitrust_Brief.pdf, Page 12`*.  
   Show the right-hand **Source Document Inspector** with highlighted text!
3. **(0:35 - 0:50) The Hallucination Guardrail Demo:**  
   Click the adversarial question: *"What is the capital of France and how do I bake sourdough bread?"*  
   Show the immediate red refusal badge: *"Notice how the AI immediately refuses to answer when evidence isn't found in firm documents. Zero hallucinations, guaranteed."*
4. **(0:50 - 1:00) The Close:**  
   *"Deployable on your local private server or dedicated VPC. Contact me today to build this for your firm!"*

---

## 💼 Fiverr Proposal Pitch Template

```text
Hi [Client Name],

I specialize in building private, high-security RAG (Retrieval-Augmented Generation) chatbots tailored specifically for law firms, medical institutions, and compliance-sensitive companies.

Key features of my custom legal RAG system:
1. 100% Data Sovereignty: Zero client data leaves your on-premise infrastructure or private cloud VPC.
2. Hard Hallucination Guardrails: Strict refusal gate ("I don't know") whenever verified evidence is absent.
3. Precision Source Citations: Direct page number, clause ID, and highlighted document excerpts for every claim.
4. Multiformat Ingestion: Search across 500+ PDFs, Word documents, case briefs, and master service agreements.

I would love to give you a 2-minute live demo showing zero-hallucination document search with exact page citations. When are you free for a quick chat?
```

---

## 💰 Recommended Fiverr Gig Pricing
* **Basic ($250 - $400):** Local document Q&A bot for up to 50 documents with basic citation.
* **Standard ($650 - $1,100):** 500+ document RAG pipeline with custom chunking, page citations, and hallucination gate.
* **Premium ($1,500 - $3,000):** Enterprise private on-premise deployment (Local Ollama/vLLM or private Azure OpenAI VPC) + Lawyer Web Portal + Document Management sync.
