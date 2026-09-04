# 💼 Daily Business Information Assistant

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB.svg?style=flat&logo=python&logoColor=white" alt="Python Version">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/FastAPI-0.104+-009688.svg?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Focus-B2B%20Sales%20Intelligence-F59E0B" alt="Focus">
  <img src="https://img.shields.io/badge/LLM-Gemini%20%7C%20DeepSeek%20%7C%20OpenAI-blueviolet" alt="AI Support">
</p>

<p align="center">
  <b>An open-source, automated B2B sales intelligence aggregator, major procurement opportunity miner, and two-dimensional matrix evaluation platform with mobile-friendly infographic digests.</b>
</p>

> [!TIP]
> 💡 **Customization Note for Open-Source Developers (100% Configurable)**:  
> This project is a completely decoupled, **generic B2B sales intelligence and tender retrieval framework**. The preset domains ("Healthcare / Education / Transport" and "Digital Transformation / AI / Data Assets / Cloud Infra") are purely **out-of-the-box demonstration templates**!  
> **You can freely reconfigure it without touching code**: simply update your target customer industries, solution domains, procurement keywords, and data sources via the modern Web Dashboard or `config/config.yaml`.

---

## 🎯 Purpose & Problems Solved

ToB sales directors and pre-sales teams face overwhelming industry noise. Most generic news mentions an industry (e.g. healthcare, education, transport) without any actionable procurement or technical scope. 

**This assistant introduces a Two-Dimensional Matrix Filter (Target Industry × Business Capability) + LLM Fact Extraction** to continuously scan national procurement portals and business media, delivering daily infographics equipped with direct tender QR codes.

---

## 🌟 Key Features

- 🎯 **[Target Industry × Business Capability] Matrix Evaluation**:
  - Requires simultaneous match between customer sectors (Healthcare, Education, Transport, Defense, Telecom) and technical solution domains (Digital Transformation & System Integration, Data Assets, AI Models, Cloud Infrastructure).
  - Flags and highlights contract awards, tenders, and framework procurements.
- 🔍 **Heterogeneous Bidding Crawlers**:
  - **China Government Procurement Network (CCGP search.ccgp.gov.cn)**: Direct authoritative portal scraping for ministries, municipal governments, and SOEs with buyer entity parsing.
  - **Baidu News Procurement Search**: Real landing page redirection resolving for fresh bidding announcements.
  - **Toutiao Bidding Opportunity Hunt**: Real-time contract award and RFP captures.
  - **Commercial & Technology RSS Feeds**: Concurrent ingestion from authoritative media.
- 🤖 **LLM Fact Extraction (Zero-Config API Base URL)**:
  - Built-in automatic provider resolution for **DeepSeek**, **Alibaba Qwen**, **Moonshot Kimi**, **Google Gemini**, **OpenAI**, and local **Ollama** (no need to manually type endpoint URLs).
  - Extracts key contract facts (buyer, awarded vendor, amount, business scope) under 30 words.
  - Robust offline rule-based fallback when offline or without API key.
- 🎨 **Sales-Tailored Color Hierarchy**:
  - Color-coded banners per industry sector (Medical Green, Education Yellow, Transport Cool Gray, Military Sand Brown, Telecom Purple).
  - Independent QR code per opportunity for instant access to the tender document.
- 💻 **Modern Web Dashboard & Headless CLI**:
  - Interactive UI with live streaming logs, matrix editor, CCGP custom keywords, and automated scheduling.

---

## 🚀 Quick Start

```bash
git clone https://github.com/stanleygll-lab/Daily_Business_Information_Assistant.git
cd Daily_Business_Information_Assistant

# Virtual environment & dependencies
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

# Copy configuration
cp .env.example .env

# Run Web Dashboard
python app.py
```
Open [http://localhost:8001](http://localhost:8001) in your browser.

---

## 📄 License

Licensed under the [MIT License](LICENSE).
