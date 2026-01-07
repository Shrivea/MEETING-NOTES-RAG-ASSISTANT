What I'm Building:
* An AI agent that converts messy meeting notes into structured, actionable data - automatically filling CRM-Style fields and generating prioritized task lists.
* Sales reps spend 2+ hours daily manually organizing meeting notes, updating CRMs, and figuring out next steps. This agent automates that entire workflow.
* Using RAG (Retrieval Augmented Generation) with Pinecone + GPT-5, the agent learns patterns from past meetings and generates structured outputs that match company workflows.

Phase 1: Populate Vector Database
├─ Use existing meeting notes from data/ directory (ACME, BUILDCO, Techstart, nextgen, dataflow)
├─ For each meeting note, create structured output examples (CRM fields + Tasks + Q&A pairs)
├─ Store in Pinecone: 
│  ├─ Vector: Embedding of raw meeting notes text
│  ├─ Metadata: Include both input (meeting notes) and output (structured format) as metadata
│  └─ This allows RAG to retrieve similar meetings and their expected output patterns
└─ Create company knowledge base with 5+ example meeting scenarios

Phase 2: Build RAG Query System
├─ Input: New meeting notes (unstructured text)
├─ Retrieve: Similar past meetings from Pinecone using vector similarity search
├─ Generate: Structured output using GPT-4 + retrieved context (few-shot learning)
└─ Output: CRM fields + prioritized tasks + Q&A pairs

Phase 3: Approval & Execution Flow
├─ Display generated output for human review
├─ User approves/edits
└─ Simulate execution (mock API calls)

EXAMPLES of MESSAGES:
    Met with Sarah from Acme Corp. She needs quote by Friday for 50 
    enterprise licenses. Discussed Salesforce integration. Main concern 
    is budget - they're comparing us to competitors.

    Follow-up call with existing customer TechStart. They want to expand 
    from 20 to 100 seats next quarter. Sarah mentioned their CFO needs 
    to approve anything over $50K.

    Discovery call with Jane from BuildCo. Early stage, just learning 
    about our product. Interested in demo. Timeline: exploring solutions 
    for Q2 implementation.

OUTPUT: We want to be able to summarize the data into 3 different parts: 

    STRUCTURED: CRM-style 
        Contact: Sarah Chen
        Company: Acme Corp
        Deal Size: 50 licenses (~$50K)
        Stage: Negotiation
        Urgency: HIGH
        Close Date: This week (Friday deadline)
        Pain Points: 
        - Budget concerns
        - Competitive pressure
        Key Discussion: Salesforce integration requirements

    TASK-Priority: TASKS
        HIGH PRIORITY (This Week)
        ├─ Task: Send pricing quote
        │  ├─ Deadline: Thursday (before Friday meeting)
        │  ├─ Owner: Sales Rep
        │  └─ Details: Include competitive positioning
        │
        └─ Task: Prepare Salesforce integration doc
        ├─ Deadline: Friday
        ├─ Owner: Solutions Engineer
        └─ Details: Technical specs for Sarah's team

        MEDIUM PRIORITY (Next Week)
        └─ Task: Schedule follow-up after quote review
        ├─ Deadline: Monday
        └─ Owner: Sales Rep

        LOW PRIORITY (Ongoing)
        └─ Task: Add to competitive deal tracking
        └─ Owner: Sales Ops

    QUESTION-ANSWER FORMAT: Q/A; YOU ONLY ASK QUESTION, 
        Q: "What companies did we meet with this week?"
        A: ACME Corp, TechStart, BuildCo, DataFlow Systems, NexGen Solutions

        Q: "Who is our contact at ACME Corp?"
        A: Sarah Chen, VP Operations

        Q: "What's the deal size for DataFlow Systems?"
        A: 75 licenses, budget approved at ~$60K

        Q: "When is the ACME Corp quote due?"
        A: Friday, January 10th (HIGH urgency deadline)

        Q: "Which customers need Salesforce integration?"
        A: ACME Corp - it's critical for their deal