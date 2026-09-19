---
name: pubmed
description: Search PubMed database for academic literature using E-utilities API. Use when the user wants to search for scientific papers, do literature reviews, find research articles, or export citations. Supports multi-dimensional search strategies (clinical trials, guidelines, reviews), automatic deduplication, and comprehensive result analysis. Trigger when user mentions "PubMed", "文献检索", "literature review", "查文献", "找论文", or needs evidence-based research.
---

# PubMed Literature Search

This skill helps you search PubMed database for academic literature using proven multi-dimensional search strategies, retrieve comprehensive paper metadata, and prepare publication-ready literature reviews.

## When to Use

Use this skill when the user:
- Wants to search PubMed for research papers on a specific topic
- Needs to do a systematic literature review or meta-analysis
- Asks to find clinical evidence (trials, guidelines, reviews)
- Wants to export citation data for academic writing
- Mentions "PubMed", "文献", "literature", "papers", "citations", "查文献", "找论文"
- Needs evidence-based research for clinical decision-making

## Instructions

### Step 1: Understand the Search Request

First, clarify with the user:
- **Search keywords**: What topic/keywords to search (use English medical/scientific terms)
- **Date range**: How many years back to search (default: 10 years for comprehensive reviews, 5 years for recent advances)
- **Search strategy**: Single comprehensive search OR multi-dimensional search by article type
- **Number of results**: How many papers per category (default: 50 per type, max 100)
- **Specific needs**: Clinical trials? Guidelines? Reviews? Meta-analyses?

### Step 2: Choose Search Strategy

**Strategy A: Multi-Dimensional Search (Recommended for Systematic Reviews)**

When the user needs comprehensive evidence, use multiple targeted searches:

1. **Clinical Trials**: `Clinical Trial[pt] OR Randomized Controlled Trial[pt]`
2. **Guidelines**: `Guideline[pt] OR Practice Guideline[pt] OR guideline[ti]`
3. **Reviews**: `Review[pt] OR Systematic Review[pt] OR Meta-Analysis[pt]`
4. **Specific Interventions**: Target specific drugs, procedures, or treatments

Benefits:
- More comprehensive coverage
- Better categorization for analysis
- Easier to identify evidence gaps
- Automatic deduplication across searches

**Strategy B: Single Comprehensive Search**

For quick overviews or when the user has a very specific query, use a single broad search with appropriate filters.

### Step 3: Create Search Script

Write a Python script using PubMed E-utilities API with these enhancements:

```python
import os
import requests
import csv
import time
import sys
from datetime import datetime
from xml.etree import ElementTree as ET

# Fix Windows console encoding (IMPORTANT for Chinese Windows systems)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# API Key（可选）- 从环境变量读取，未设置则匿名访问（3次/秒，功能不受影响）
# 免费申请: https://www.ncbi.nlm.nih.gov/account/settings/
NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "")

def search_pubmed(query, max_results=50, years=10, article_type=None, api_key=NCBI_API_KEY):
    """
    Search PubMed using E-utilities API

    Parameters:
    - query: Search terms (e.g., "chronic kidney disease iron deficiency anemia")
    - max_results: Maximum number of papers to retrieve
    - years: Number of years to look back
    - article_type: Optional filter (e.g., "Clinical Trial", "Review", "Guideline")
    - api_key: NCBI API key for faster requests (default: configured)
    """

    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    # Calculate date range
    current_year = datetime.now().year
    start_year = current_year - years

    # Build search query with date filter
    date_filter = f"{start_year}:{current_year}[pdat]"
    full_query = f"({query}) AND {date_filter}"

    if article_type:
        full_query += f" AND {article_type}[pt]"

    print(f"Search query: {full_query}")

    # Step 1: Search for PMIDs
    search_url = f"{base_url}/esearch.fcgi"
    search_params = {
        "db": "pubmed",
        "term": full_query,
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance"
    }

    if api_key:
        search_params["api_key"] = api_key

    response = requests.get(search_url, params=search_params)
    data = response.json()
    pmids = data["esearchresult"]["idlist"]

    print(f"Found {len(pmids)} papers")

    # Step 2: Fetch details for each PMID
    fetch_url = f"{base_url}/efetch.fcgi"
    papers = []

    for i, pmid in enumerate(pmids):
        fetch_params = {
            "db": "pubmed",
            "id": pmid,
            "retmode": "xml"
        }

        if api_key:
            fetch_params["api_key"] = api_key

        response = requests.get(fetch_url, params=fetch_params)

        # Parse XML response
        root = ET.fromstring(response.content)

        article = root.find(".//PubmedArticle")
        if article is None:
            continue

        # Extract title
        title_elem = article.find(".//ArticleTitle")
        title = title_elem.text if title_elem is not None else "N/A"

        # Extract authors
        authors = []
        for author in article.findall(".//Author"):
            lastname = author.find("LastName")
            forename = author.find("ForeName")
            if lastname is not None:
                name = lastname.text
                if forename is not None:
                    name += f" {forename.text[0]}"
                authors.append(name)

        # Extract journal
        journal_elem = article.find(".//Journal/Title")
        journal = journal_elem.text if journal_elem is not None else "N/A"

        # Extract year
        year_elem = article.find(".//PubDate/Year")
        if year_elem is None:
            year_elem = article.find(".//PubDate/MedlineDate")
        year = year_elem.text[:4] if year_elem is not None else "N/A"

        # Extract abstract
        abstract_parts = article.findall(".//Abstract/AbstractText")
        abstract = " ".join([p.text or "" for p in abstract_parts])

        # Extract publication type (NEW)
        pub_types = [pt.text for pt in article.findall(".//PublicationType")]
        pub_type = "; ".join(pub_types) if pub_types else "N/A"

        papers.append({
            "PMID": pmid,
            "Title": title,
            "Authors": "; ".join(authors[:5]) + ("..." if len(authors) > 5 else ""),
            "Year": year,
            "Journal": journal,
            "Publication_Type": pub_type,  # NEW
            "Abstract": abstract,
            "PubMed_URL": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"  # NEW
        })

        print(f"Processed {i+1}/{len(pmids)}: {title[:60]}...")

        # Rate limiting: 10 requests/second with API key
        time.sleep(0.1 if api_key else 0.4)

    return papers

def save_to_csv(papers, filename="pubmed_results.csv"):
    """Save papers to CSV file with UTF-8-BOM encoding for Excel compatibility"""
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig for Excel
        writer = csv.DictWriter(f, fieldnames=["PMID", "Title", "Authors", "Year", "Journal", "Publication_Type", "Abstract", "PubMed_URL"])
        writer.writeheader()
        writer.writerows(papers)
    print(f"\nSaved {len(papers)} papers to {filename}")

# Example: Multi-dimensional search with deduplication
print("=" * 80)
print("Search 1: Clinical Trials")
print("=" * 80)
papers_trials = search_pubmed(
    query='("chronic kidney disease" OR CKD) AND ("iron deficiency anemia" OR IDA)',
    max_results=50,
    years=10,
    article_type="Clinical Trial[pt] OR Randomized Controlled Trial[pt]"
)

print("\n" + "=" * 80)
print("Search 2: Guidelines")
print("=" * 80)
papers_guidelines = search_pubmed(
    query='("chronic kidney disease" OR CKD) AND ("iron deficiency anemia" OR IDA)',
    max_results=30,
    years=10,
    article_type="Guideline[pt] OR Practice Guideline[pt]"
)

print("\n" + "=" * 80)
print("Search 3: Reviews")
print("=" * 80)
papers_reviews = search_pubmed(
    query='("chronic kidney disease" OR CKD) AND ("iron deficiency anemia" OR IDA)',
    max_results=50,
    years=10,
    article_type="Review[pt] OR Systematic Review[pt]"
)

# Merge and deduplicate
all_papers = papers_trials + papers_guidelines + papers_reviews
seen_pmids = set()
unique_papers = []
for paper in all_papers:
    if paper["PMID"] not in seen_pmids:
        seen_pmids.add(paper["PMID"])
        unique_papers.append(paper)

# Save results
save_to_csv(unique_papers, "literature_review.csv")

# Print statistics
print("\n" + "=" * 80)
print(f"Search completed! Found {len(unique_papers)} unique papers")
print("=" * 80)
print("\nBreakdown by category:")
print(f"- Clinical Trials: {len(papers_trials)} papers")
print(f"- Guidelines: {len(papers_guidelines)} papers")
print(f"- Reviews: {len(papers_reviews)} papers")
```

### Key Improvements in This Version:

1. **Windows Encoding Fix**: `sys.stdout.reconfigure(encoding='utf-8')` prevents console errors on Chinese Windows
2. **Publication Type Field**: Helps categorize papers (Clinical Trial, Review, Meta-Analysis, etc.)
3. **PubMed URL**: Direct links for easy access
4. **UTF-8-BOM Encoding**: `utf-8-sig` ensures Excel opens CSV files correctly without garbled Chinese characters
5. **Deduplication**: Automatically removes duplicate papers across multiple searches
6. **Search Statistics**: Shows breakdown by category for better analysis

### Step 4: Run and Verify

1. Save the script to a file (e.g., `pubmed_search_<topic>.py`)
2. Run the script: `python pubmed_search_<topic>.py`
3. Verify the CSV output:
   - Check for duplicate PMIDs (should be none after deduplication)
   - Verify all fields are populated correctly
   - Open in Excel to confirm no encoding issues
   - Review the statistics summary

### Step 5: Follow-up Analysis (Optional)

After retrieving papers, offer to:
- **Classify papers** by research type and quality (RCT, cohort, case-control, etc.)
- **Summarize key findings** from abstracts using structured extraction
- **Generate statistics**: 
  - Publication trends over time
  - Top journals and impact factors
  - Geographic distribution of research
  - Common keywords and MeSH terms
- **Create citation lists** in various formats:
  - GB/T 7714-2015 (Chinese standard)
  - Vancouver (medical journals)
  - APA 7th edition
  - EndNote/Zotero import format
- **Write literature review draft** with:
  - Evidence hierarchy analysis
  - Quality assessment (GRADE, Cochrane Risk of Bias)
  - Synthesis of findings by outcome
  - Identification of research gaps

## Search Tips

### Multi-Dimensional Search Patterns (Proven Strategies)

**Pattern 1: Disease + Intervention + Evidence Type**
```python
# Example: CKD + Iron Therapy
searches = [
    ('Clinical Trials', 'Clinical Trial[pt] OR Randomized Controlled Trial[pt]', 50),
    ('Guidelines', 'Guideline[pt] OR Practice Guideline[pt] OR guideline[ti]', 30),
    ('Reviews', 'Review[pt] OR Systematic Review[pt] OR Meta-Analysis[pt]', 50),
    ('Specific Drug', '(roxadustat OR "FG-4592") AND iron', 30)
]
```

**Pattern 2: Comparative Effectiveness**
```python
# Example: Comparing iron formulations
searches = [
    ('IV Iron', '("intravenous iron" OR "parenteral iron") AND CKD', 50),
    ('Oral Iron', '("oral iron" OR "ferrous sulfate") AND CKD', 50),
    ('Head-to-head', '("intravenous iron" OR "oral iron") AND comparative', 30)
]
```

**Pattern 3: Safety and Efficacy**
```python
# Example: Drug safety profile
searches = [
    ('Efficacy', 'drug_name AND (efficacy OR effectiveness) AND RCT', 50),
    ('Safety', 'drug_name AND (safety OR adverse OR toxicity)', 50),
    ('Real-world', 'drug_name AND ("real world" OR observational)', 30)
]
```

### Common PubMed Filters

**Article Types:**
- `Clinical Trial[pt]` - Clinical trials
- `Randomized Controlled Trial[pt]` - RCTs specifically
- `Review[pt]` - Review articles
- `Systematic Review[pt]` - Systematic reviews
- `Meta-Analysis[pt]` - Meta-analyses
- `Guideline[pt]` - Clinical practice guidelines
- `Practice Guideline[pt]` - Practice guidelines
- `Comparative Study[pt]` - Comparative studies

**Study Populations:**
- `Humans[mh]` - Human studies only
- `Animals[mh]` - Animal studies
- `Adult[mh]` - Adult population
- `Child[mh]` - Pediatric population

**Languages and Availability:**
- `English[la]` - English language
- `Free full text[sb]` - Free full text available
- `Abstract available[sb]` - Has abstract

### Boolean Operators and Advanced Syntax

**Basic Operators:**
- `AND` - Both terms must appear
- `OR` - Either term can appear
- `NOT` - Exclude term
- Use parentheses for grouping: `(osteoarthritis OR "cartilage repair")`

**Field Tags:**
- `[ti]` - Title
- `[tiab]` - Title/Abstract
- `[au]` - Author
- `[ta]` - Journal abbreviation
- `[pt]` - Publication type
- `[mh]` - MeSH terms
- `[pdat]` - Publication date

**Proximity Operators:**
- `"exact phrase"` - Exact phrase match
- `term*` - Wildcard (e.g., `therap*` matches therapy, therapeutic, therapeutics)

### Example Queries (Real-World Tested)

**Comprehensive Disease Review:**
```
("chronic kidney disease" OR CKD OR "renal insufficiency") 
AND ("iron deficiency anemia" OR "iron deficiency anaemia" OR IDA) 
AND ("Clinical Trial"[pt] OR "Randomized Controlled Trial"[pt])
AND 2015:2026[pdat]
```

**Drug-Specific Evidence:**
```
(roxadustat OR "FG-4592" OR "爱瑞卓") 
AND (iron OR "iron therapy" OR "iron supplementation") 
AND ("chronic kidney disease" OR CKD)
AND English[la]
```

**Guideline Search:**
```
("iron deficiency anemia" OR IDA) 
AND (guideline[ti] OR "practice guideline"[pt] OR "clinical practice guideline") 
AND (KDIGO OR KDOQI OR ESC OR "European Society")
```

**Safety Profile:**
```
("ferric carboxymaltose" OR "iron carboxymaltose" OR Ferinject) 
AND (safety OR "adverse events" OR hypophosphatemia OR "adverse reactions")
AND ("systematic review"[pt] OR "meta-analysis"[pt])
```

## Important Notes

1. **Use English keywords** - PubMed is an English database, but you can include drug brand names in Chinese for comprehensive searches
2. **Abstracts only** - Full text is not available through the API (but PubMed URLs are provided for manual access)
3. **Verify citations** - Always double-check important references before publication
4. **Reasonable limits** - Stay under 100 papers per search category to avoid timeouts
5. **Windows encoding** - The script includes automatic UTF-8 configuration for Chinese Windows systems
6. **Excel compatibility** - CSV files use UTF-8-BOM encoding to prevent garbled characters in Excel
7. **Deduplication** - Always deduplicate when running multiple searches to avoid counting papers twice
8. **Search statistics** - Present category breakdowns to help users understand evidence distribution
9. **API key is optional** - Works anonymously at 3 req/s; set the `NCBI_API_KEY` environment variable (free from NCBI) for 10 req/s

## Troubleshooting

**Problem: Console shows garbled Chinese characters**
- Solution: The script includes `sys.stdout.reconfigure(encoding='utf-8')` for Windows

**Problem: Excel shows garbled Chinese in CSV**
- Solution: Use `encoding="utf-8-sig"` instead of `encoding="utf-8"` when writing CSV

**Problem: Too many duplicate papers**
- Solution: Implement deduplication using PMID as unique identifier

**Problem: Search returns too few results**
- Solution: 
  - Broaden search terms (use OR operators)
  - Increase date range (e.g., 10 years instead of 5)
  - Remove restrictive filters
  - Check spelling of medical terms

**Problem: Search returns irrelevant papers**
- Solution:
  - Use exact phrases with quotes: `"iron deficiency anemia"`
  - Add specific filters: `AND Humans[mh]`
  - Use field tags: `iron[ti]` to search only in titles
  - Add exclusion terms: `NOT animal[mh]`

## Best Practices from Successful Searches

1. **Start with multi-dimensional strategy** for systematic reviews
2. **Always include publication type** in search statistics
3. **Provide direct PubMed URLs** for easy access to full papers
4. **Show search progress** with real-time console output
5. **Print comprehensive statistics** at the end (total papers, breakdown by category)
6. **Use 10-year lookback** for comprehensive reviews, 5 years for recent advances
7. **Combine synonyms with OR**: `("iron deficiency anemia" OR "iron deficiency anaemia" OR IDA)`
8. **Include both generic and brand names** for drug searches
