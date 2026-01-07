# 🤖 Azentic - AI-Powered Meeting Notes Agent

**Transform messy meeting notes into structured CRM data, prioritized tasks, and instant answers.**

Azentic is an intelligent agent that automates the tedious work of organizing sales meeting notes. Built with RAG (Retrieval Augmented Generation), it converts unstructured text into actionable insights - automatically extracting CRM fields, generating task lists, and answering questions about your meetings.

---

## 🎯 Problem Statement

Sales reps spend **2+ hours daily** manually:
- Updating CRMs with meeting details
- Creating follow-up task lists
- Searching through past conversations
- Figuring out next steps for each customer

**Azentic automates this entire workflow.**

---

## ✨ Features

### 1. **CRM Data Extraction** 📊
Automatically extracts structured fields from meeting notes:
- Contact information
- Company details
- Deal size and stage
- Urgency level
- Pain points
- Key discussion topics

### 2. **Task Prioritization** ✅
Analyzes all meetings to generate a consolidated task list:
- Tasks organized by priority (HIGH/MEDIUM/LOW)
- Company names attached to each task
- Deadlines and ownership clearly defined
- Sorted by urgency within each priority level

### 3. **Question & Answer** 💬
Ask natural language questions about your meetings:
- "What companies did we meet with this week?"
- "Who is our contact at ACME Corp?"
- "When is the DataFlow quote due?"
- Answers based on semantic search across all meetings

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | FastAPI |
| **Vector Database** | Pinecone |
| **LLM** | OpenAI GPT-4o-mini |
| **Embeddings** | OpenAI text-embedding-3-small |
| **Language** | Python 3.9+ |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- OpenAI API key
- Pinecone API key

### Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd AZENTIC
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
# Create .env file
cat > .env << EOF
OPENAI_API_KEY=your_openai_api_key_here
PINECONE_API_KEY=your_pinecone_api_key_here
EOF
```

5. **Populate the vector database**
```bash
python vdb.py
```

6. **Start the server**
```bash
uvicorn app:app --reload
```

Server runs at `http://localhost:8000`

---

## 📖 API Documentation

### **1. CRM Data Extraction**

**Endpoint:** `POST /crm-data`

**Request:**
```json
{
  "vector_id": "meeting-acme"
}
```

**Response:**
```json
{
  "status": "success",
  "vector_id": "meeting-acme",
  "data": {
    "contact": "Sarah Chen, VP Operations",
    "company": "ACME Corp",
    "deal_size": "50 licenses (~$45K)",
    "stage": "Negotiation",
    "urgency": "HIGH"
  },
  "formatted": "CRM DATA:\n..."
}
```

**Available Meeting IDs:**
- `meeting-acme`
- `meeting-techstart`
- `meeting-buildco`
- `meeting-dataflow`
- `meeting-nextgen`

---

### **2. Task Prioritization**

**Endpoint:** `POST /task-data`

**Request:**
```json
{
  "meeting_notes": null  // Optional: add new meeting notes
}
```

**Response:**
```json
{
  "status": "success",
  "tasks": "HIGH PRIORITY (This Week)\n├─ Task: Send quote - ACME\n...",
  "meetings_analyzed": 5,
  "formatted_output": "TASK PRIORITY LIST\n..."
}
```

**Example with New Meeting:**
```json
{
  "meeting_notes": "URGENT: Met with ZetaCorp CEO. Need proposal by Friday..."
}
```

---

### **3. Question & Answer**

**Endpoint:** `POST /question-answer-data`

**Request:**
```json
{
  "question": "What companies did we meet with this week?"
}
```

**Response:**
```json
{
  "status": "success",
  "question": "What companies did we meet with this week?",
  "answer": "We met with ACME Corp, TechStart, BuildCo, DataFlow Systems, and NexGen Solutions.",
  "meetings_used": 5,
  "formatted_output": "QUESTION & ANSWER\n..."
}
```

---

## 🧪 Testing

Run test scripts for each endpoint:

```bash
# Test CRM extraction
python test_crm.py

# Test task prioritization
python test_tasks.py

# Test Q&A
python test_qa.py
```

---

## 📁 Project Structure

```
AZENTIC/
├── app.py                 # FastAPI application with all endpoints
├── vdb.py                 # Vector database setup and population
├── CRM.py                 # CRM data extraction logic
├── task.py                # Task prioritization logic
├── questions.py           # Q&A logic
├── data/                  # Sample meeting notes
│   ├── acme.txt
│   ├── techstart.txt
│   ├── buildco.txt
│   ├── dataflow.txt
│   └── nextgen.txt
├── test_crm.py           # CRM endpoint tests
├── test_tasks.py         # Task endpoint tests
├── test_qa.py            # Q&A endpoint tests
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (not in repo)
└── README.md            # This file
```

---

## 🔍 How It Works

### **RAG (Retrieval Augmented Generation) Architecture**

```
User Input → Embed Query → Search Pinecone → Retrieve Context → GPT Generates → Structured Output
```

1. **Embedding:** Convert text to vectors using OpenAI's embedding model
2. **Storage:** Store meeting embeddings in Pinecone with metadata
3. **Retrieval:** Search for relevant meetings using semantic similarity
4. **Generation:** Use GPT-4o-mini with retrieved context to generate outputs

### **Why RAG?**

- **Accuracy:** Responses grounded in actual meeting data
- **Scalability:** Works with any number of meetings
- **Flexibility:** No retraining needed for new meetings
- **Context-aware:** Learns patterns from similar past meetings

---

## 📊 Sample Data

The project includes 5 sample meetings:

| Company | Contact | Deal Size | Stage |
|---------|---------|-----------|-------|
| ACME Corp | Sarah Chen | 50 licenses (~$45K) | Negotiation |
| TechStart | Mike Patterson | 100 seats (~$2.5K) | Expansion |
| BuildCo | Jane Martinez | 30 seats | Discovery |
| DataFlow Systems | Marcus Johnson | 75 seats (~$60K) | Hot Lead |
| NexGen Solutions | Rebecca Torres | 45 seats (+ 15 upsell) | Renewal |

---

## ⚡ Performance

- **CRM Extraction:** ~2-3 seconds per meeting
- **Task Prioritization:** ~150-180 seconds (5 meetings)
- **Q&A:** ~5-10 seconds per question
- **Model:** GPT-4o-mini (fast, cost-effective)

---

## 🔮 Future Enhancements

- [ ] Add email integration (Gmail, Outlook)
- [ ] Support for uploading new meetings via UI
- [ ] Real-time CRM sync (Salesforce, HubSpot)
- [ ] Multi-language support
- [ ] Voice meeting transcription integration
- [ ] Analytics dashboard
- [ ] Automated follow-up email generation
- [ ] Calendar integration for deadline tracking

---

## 🐛 Troubleshooting

### **"Index not found" error**
```bash
python vdb.py  # Recreate and populate database
```

### **"Module not found" error**
```bash
pip install -r requirements.txt
```

### **Slow response times**
- Using GPT-4o-mini (fast model) ✓
- Consider reducing context length if needed
- Check internet connection

### **Empty/incorrect responses**
- Verify .env file has valid API keys
- Check that meetings are in database: `python vdb.py`
- Ensure meeting IDs are correct (e.g., "meeting-acme")

---

## 📝 License

MIT License - feel free to use this project for your own purposes!

---

## 🙏 Acknowledgments

Built as part of the Azentic coding assessment, demonstrating:
- RAG implementation with Pinecone + OpenAI
- API design with FastAPI
- Practical AI application for sales automation
- System design and scalability considerations

---

## 📧 Contact

For questions or feedback, reach out at [your-email@example.com]

---

**⭐ If you find this project helpful, consider starring the repository!**
