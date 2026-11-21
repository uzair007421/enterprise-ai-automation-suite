# 👥 Project 06: Bias-Free AI Recruiter Assistant & Auto-Scheduler

> **Commercial Brief:**  
> *"We receive 500 CVs per job. Screen them against the job description, score fairly, explain each score, schedule interviews for shortlisted candidates, and never use gender, age or name in scoring."*

---

## 🌟 Key Capabilities
* **Strict Anonymization Gateway:** Strips applicant Name, Gender, Age, Pronouns, Photos, and Location proxies before evaluation to prevent unconscious algorithmic bias.
* **100-Point Explainable Rubric:** Evaluates candidates across Technical Competencies (40), Verified Experience Depth (30), Proven Project Impact (20), and Best Practices (10).
* **Autonomous Calendar Scheduling:** Candidates who meet or exceed the shortlist threshold (80+) receive automated Google Calendar / Calendly interview booking invites.
* **Immutable Compliance Audit Trail:** Generates an EEOC & GDPR audit attestation proving that scoring was based solely on verified job requirements.

---

## 🏗️ Architecture & Screening Flow

```
                  [ 500+ Incoming Resumes / CVs ]
                                │
                                ▼
         [ Anonymization & Demographic Redaction Gateway ]
         (Strips Name, Age, Gender, Pronouns, Photos)
                                │
                                ▼
         [ Structured 100-Point Job Rubric Evaluation ]
          • Technical Skills Fit (40 pts)
          • Experience Depth (30 pts)
          • Quantified Commercial Impact (20 pts)
          • Engineering Best Practices (10 pts)
                                │
                   ┌────────────┴────────────┐
                   ▼                         ▼
         [ Score >= 80 (Shortlist) ]   [ Score < 80 (Nurture) ]
                   │                         │
                   ▼                         ▼
      [ Google Calendar Auto-Sync ]   [ Constructive Feedback ]
      • Dispatch Calendly invite       • Maintain candidate pool
      • Slot: Round 1 Technical        • No wasted recruiter hours
```

---

## ⚡ How to Run Live Interactive Demo

Zero external pip dependencies required. Runs completely using Python standard library:

```bash
cd 06-hr-ai-recruiter-assistant
python run_demo.py
```
Open your browser at: **`http://localhost:8006`**

---

## 🎥 60-Second Fiverr Video Recording Script
1. **(0:00 - 0:15) The Hook:**  
   *"HR departments drown in hundreds of resumes per job post, and unconscious hiring bias leads to legal risk and bad hires. Here is our Bias-Free AI Recruiter Assistant."*
2. **(0:15 - 0:35) The Blind Screening & Rubric Score:**  
   Show the candidate card in **Blind Anonymized View**: *"Notice the AI strips names, genders, and ages completely. It evaluates strictly on technical competence, experience depth, and verified project impact."*
3. **(0:35 - 0:45) The Reveal Switch & Auto-Calendar:**  
   Toggle the **HR Revealed View**: *"Once scored fairly, top candidates scoring over 80 points automatically receive a Google Calendar invitation for Round 1 technical interviews without recruiter manual work."*
4. **(0:45 - 1:00) Compliance Audit Trail:**  
   Point to the EEOC audit log: *"Every decision produces an immutable compliance attestation. Contact me to build this fair hiring automation for your agency!"*

---

## 💼 Fiverr Proposal Pitch Template

```text
Hi [Client Name],

I noticed you are looking to automate candidate resume screening and interview scheduling while strictly eliminating hiring bias.

I have already engineered a Bias-Free AI Recruiter Assistant featuring:
1. Demographic Redaction Gateway: Strips names, gender pronouns, and age indicators to guarantee fair evaluations.
2. 100-Point Structured Rubric: Detailed point breakdowns and plain-English scoring explanations.
3. Automated Calendar Booking: Auto-generates Google Calendar / Calendly invites for candidates meeting the 80+ threshold.
4. EEOC & GDPR Compliance Audit Trail: Certified log proving zero demographic attributes influenced the score.

I can deploy this for your recruitment pipeline within 3 to 5 business days. Let's connect on chat for a quick live walkthrough!
```

---

## 💰 Recommended Fiverr Gig Pricing
* **Basic ($200 - $350):** Resume text parser and skill extractor to Google Sheets.
* **Standard ($500 - $850):** Blind screening engine + 100-point rubric + Interview booking link generator.
* **Premium ($1,200 - $2,200):** Full Applicant Tracking System (ATS) webhook sync + EEOC compliance reporting + Greenhouse / Lever API integration.
