import os
import requests
import csv
import time
from datetime import datetime
from xml.etree import ElementTree as ET
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# API Key（可选）- 从环境变量 NCBI_API_KEY 读取；未设置则匿名访问（3次/秒）
NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "")

def create_session():
    """创建带有重试机制的session"""
    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def search_pubmed(query, max_results=50, years=5, article_type=None, api_key=NCBI_API_KEY):
    """Search PubMed using E-utilities API"""
    session = create_session()
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    current_year = datetime.now().year
    start_year = current_year - years

    date_filter = f"{start_year}:{current_year}[pdat]"
    full_query = f"({query}) AND {date_filter}"

    if article_type:
        full_query += f" AND {article_type}[pt]"

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

    print(f"Search query: {full_query}")

    try:
        response = session.get(search_url, params=search_params, timeout=60)
        response.raise_for_status()
        data = response.json()
        pmids = data["esearchresult"]["idlist"]
        print(f"Found {len(pmids)} papers")
    except Exception as e:
        print(f"Search error: {e}")
        return []

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

        for attempt in range(3):
            try:
                response = session.get(fetch_url, params=fetch_params, timeout=60)
                response.raise_for_status()
                root = ET.fromstring(response.content)

                article = root.find(".//PubmedArticle")
                if article is None:
                    continue

                # Extract title
                title_elem = article.find(".//ArticleTitle")
                title = title_elem.text if title_elem is not None and title_elem.text else "N/A"

                # Extract authors
                authors = []
                for author in article.findall(".//Author"):
                    lastname = author.find("LastName")
                    forename = author.find("ForeName")
                    if lastname is not None and lastname.text:
                        name = lastname.text
                        if forename is not None and forename.text:
                            name += f" {forename.text[0]}"
                        authors.append(name)

                # Extract journal
                journal_elem = article.find(".//Journal/Title")
                journal = journal_elem.text if journal_elem is not None and journal_elem.text else "N/A"

                # Extract year
                year_elem = article.find(".//PubDate/Year")
                if year_elem is None:
                    year_elem = article.find(".//PubDate/MedlineDate")
                year = year_elem.text[:4] if year_elem is not None and year_elem.text else "N/A"

                # Extract abstract
                abstract_parts = article.findall(".//Abstract/AbstractText")
                abstract = " ".join([p.text or "" for p in abstract_parts if p.text])

                papers.append({
                    "PMID": pmid,
                    "Title": title,
                    "Authors": "; ".join(authors[:5]) + ("..." if len(authors) > 5 else ""),
                    "Year": year,
                    "Journal": journal,
                    "Abstract": abstract[:500] + "..." if len(abstract) > 500 else abstract
                })

                print(f"[{i+1}/{len(pmids)}] {title[:60]}...")
                break

            except Exception as e:
                if attempt < 2:
                    print(f"[{i+1}/{len(pmids)}] Retry {attempt+1} for PMID {pmid}...")
                    time.sleep(2)
                else:
                    print(f"[{i+1}/{len(pmids)}] Error processing PMID {pmid}: {e}")

        time.sleep(0.2)

    return papers

def save_to_csv(papers, filename):
    """Save papers to CSV file"""
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["PMID", "Title", "Authors", "Year", "Journal", "Abstract"])
        writer.writeheader()
        writer.writerows(papers)
    print(f"\nSaved {len(papers)} papers to {filename}")

# 搜索轻度儿童地中海贫血铁营养管理
query = """
(thalassemia minor OR thalassemia trait OR mild thalassemia OR "beta thalassemia trait" OR "alpha thalassemia trait")
AND
(child* OR pediatric OR paediatric OR infant OR adolescent)
AND
(iron OR "iron nutrition" OR "iron supplementation" OR "iron status" OR "iron intake" OR "iron deficiency" OR "iron overload" OR "dietary iron" OR "iron metabolism")
"""

print("=" * 60)
print("PubMed 文献搜索")
print("主题: 轻度儿童地中海贫血的铁营养管理")
print("=" * 60)

papers = search_pubmed(query, max_results=50, years=5)
output_file = "thalassemia_iron_results.csv"

if papers:
    save_to_csv(papers, output_file)

    print("\n" + "=" * 60)
    print("搜索结果摘要")
    print("=" * 60)
    for i, p in enumerate(papers[:10], 1):
        print(f"\n[{i}] {p['Title']}")
        print(f"    作者: {p['Authors']}")
        print(f"    年份: {p['Year']} | 期刊: {p['Journal']}")
        print(f"    PMID: {p['PMID']}")

    if len(papers) > 10:
        print(f"\n... 还有 {len(papers) - 10} 篇文献，详见CSV文件")
else:
    print("未找到文献或网络连接失败")
