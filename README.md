

## General

Hi :)

This readme aim to help you quickly run and test the assigment.

I noticed the assigment doc included many interesting questions. 
To make sure I adress all of them, I created a copy of the doc and wrote my answers in green throught the document [here](https://docs.google.com/document/d/1M7eennoHPUwDbBiedJ6j1lvDYqKAvrOSYNjBk0f1xQw/edit?usp=sharing) 

For any issues or questions, please contact me:

Taisya
054-870-870-7
stasya@gmail.com

## Setup Instructions 

**1. Clone the repository: [TODO - add link]**
```bash
git clone 
```
**1. Run setup:**  
```bash
make setup
```
**3. Activate virtual env (as per previous step instructions)**

**4. Create a `.env` file.**
```bash
cp .env.example .env
```
**5. Update API keys in .env**
```python
OPENAI_API_KEY=
TAVILY_API_KEY = 
```
**6. Run docker (for postges db)**
```bash
make run-docker
```

## How to Run Test Queries 
**1. Run indexing**
```bash
 python cli.py index
```
** Current logging level is DEBUG, which gives a lot of information on the indexing process and statistics for each indexing step.
Adjust to INFO in the .env if you want a less verbosse version

**2. Run test queries**
```bash
make test
```
or use cli directly:
```bash
python cli.py query "Your question here"
```

**Example test results**
```
(.venv) taisya@DESKTOP-T293T7K:rag-research-agent-template (main)$ make test
🧪 Running test questions... 
.venv/bin/python test_cli_questions.py
🚀 Running 2 questions starting from index 0...
================================================================================

📝 Question 1/2: What are Apple's top 3 risk factors mentioned in their latest 10-K, and what percentage of total revenue did they spend on R&D?
--------------------------------------------------------------------------------
🔧 Executing: generate_response
🔧 Executing tool: get_agent_available_data()
🔧 Executing: generate_response
🔧 Executing tool: document_qa(query="Apple's top 3 risk factors in 2025 10-K")
🔧 Executing tool: document_qa(query='percentage of total revenue spent on R&D in 2025 10-K')
🔧 Executing: generate_response
🔧 Executing: validate_citations
💡 Answer: - **Top 3 Risk Factors:**
  1. Macroeconomic and Industry Risks: Apple's operations and performance depend significantly on global and regional economic conditions. Adverse conditions, such as slow growth, high unemployment, and inflation, can materially affect Apple's business and stock price [Item 1A | pages ['5', '6']](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm#i719388195b384d85a4e238ad88eba90a_52).
  2. Political and Geopolitical Risks: Political events, trade disputes, and geopolitical tensions can have a material adverse effect on Apple and its supply chain [Item 1A | pages ['5', '6']](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm#i719388195b384d85a4e238ad88eba90a_52).
  3. Tariffs and Trade Measures: New U.S. tariffs and retaliatory measures from other countries can impact Apple's supply chain, pricing, and gross margin [Item 7 | pages ['22', '22']](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm#i719388195b384d85a4e238ad88eba90a_94).

- **Percentage of Total Revenue Spent on R&D:**
  - Apple spent 8% of its total net sales on research and development in 2025 [Item 7 | pages ['24', '25']](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm#i719388195b384d85a4e238ad88eba90a_94).

================================================================================

📝 Question 2/2: How does Apple's gross margin compare to Microsoft's current gross margin, and what reasons does Apple cite in their 10-K for any margin pressure?
--------------------------------------------------------------------------------
🔧 Executing: generate_response
🔧 Executing tool: document_qa(query='Apple gross margin reasons for pressure')
🔧 Executing tool: search(query='Microsoft current gross margin 2025')
🔧 Executing: generate_response
🔧 Executing: validate_citations
💡 Answer: ### Apple's Gross Margin and Reasons for Pressure:
- **Gross Margin**: Apple's total gross margin for 2025 was $195,201 million, with a gross margin percentage that saw fluctuations due to various factors [Item 7 | pages ['24', '24']](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm#i719388195b384d85a4e238ad88eba90a_94).
- **Reasons for Margin Pressure**:
  - Tariff costs and a different mix of products affected the products' gross margin percentage.
  - Macroeconomic conditions, including inflation, interest rates, and currency fluctuations, impacted Apple's financial condition.
  - New U.S. tariffs introduced in 2025 on imports from several countries, including China and the EU, posed challenges [Item 7 | pages ['22', '22']](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm#i719388195b384d85a4e238ad88eba90a_94)[Item 7 | pages ['24', '25']](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm#i719388195b384d85a4e238ad88eba90a_94).

### Microsoft's Current Gross Margin:
- **Gross Margin**: Microsoft's gross profit margin for the fiscal year ending June 2025 was 68.82% [source](https://www.alphaquery.com/stock/MSFT/fundamentals/annual/gross-margin).

================================================================================
✅ All questions completed!
(.venv) taisya@DESKTOP-T293T7K:rag-research-agent-template (main)$ 
```

## Architecture Overview 

For detailed architecture documentation, see [Architecture Documentation](docs/architecture.md).
For an even deeper dive into algorithms see my comments in green [here](https://docs.google.com/document/d/1M7eennoHPUwDbBiedJ6j1lvDYqKAvrOSYNjBk0f1xQw/edit?usp=sharing)  

## Dependencies 
- **Langragh** - my framework of choice for agents. I ususally use Langragh for orchestration, and LlamaIndex for RAG, but here I decided to experiment and  try our a Langragh only approach and an indexing agent (though a very simple one).

- **postgres + pgvector** - a reasonably good vector store I have expirience with. I like it because it enables to have a single DB for vector search and application data. 

- **BeautifulSoup** - for parsing html

- **EdgarTools** - Becasue the exercise was meant for 4 hours, I assumed there is a library the parses 10-K documents well, and will enable me to use the time for agent logic, prompts and chunk data modeling. 
Unfortunately, after trying several libraries, node gave me the ability to preserve both document structure and table references in the way I needed, and I ended up doing my own parsing. I did still use Edgartools for loading the file, and this enables to load any file according to agent confic, which is nice. I also used some of the metadata in it instead of parsing everything mysefl.

- **Jinja** - I like managing prompts with jinja, allows to inject values, sub prompts etc, and keep prompts clean

- **loguru** - for logging

- **pandas** - I had no expirience working with tables for RAG, so chose this as my tool to handle table data. Initially I wanted to create a tool for calculations to overcome the LLM math calculation limitations, and wanted to create dataframes for this. I ended up implementing something simpler, but kept this and probably would use this for production agents. 

## What I would do if I had more time, or was dealing with production agent
 - unit and integration tests for filing parsing, structured table extraction
 - e2e agent test with LLM gudge
 - a question disambiguation node - to reliably handle "latest", "current" etc, or to ask follow up questions before continuing. 
 - more prompt tuning
 - code organization, testing, edge cases, better error handling
 - CI/CD

