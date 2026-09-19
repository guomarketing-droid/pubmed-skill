#!/usr/bin/env python3
"""
PubMed Literature Search Tool
Uses NCBI E-utilities API to search and retrieve paper metadata
"""

import os
import requests
import csv
import time
import argparse
from datetime import datetime
from xml.etree import ElementTree as ET

# NCBI API Key（可选）- 提升请求速率到10次/秒；不设置则匿名访问（3次/秒，功能不受影响）
# 免费申请: https://www.ncbi.nlm.nih.gov/account/settings/
NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "")


def search_pubmed(query, max_results=50, years=5, article_type=None, api_key=NCBI_API_KEY):
    """
    Search PubMed using E-utilities API

    Parameters:
    - query: Search terms (e.g., "mesenchymal stem cell osteoarthritis")
    - max_results: Maximum number of papers to retrieve (default: 50)
    - years: Number of years to look back (default: 5)
    - article_type: Optional filter (e.g., "Clinical Trial", "Review")
    - api_key: Optional NCBI API key for faster requests
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

    print(f"Searching PubMed for: {full_query}")
    response = requests.get(search_url, params=search_params)
    data = response.json()

    result_count = data["esearchresult"].get("count", "0")
    pmids = data["esearchresult"]["idlist"]

    print(f"Found {result_count} total results, retrieving {len(pmids)} papers...")

    if not pmids:
        print("No papers found. Try different keywords.")
        return []

    # Step 2: Fetch details for each PMID
    fetch_url = f"{base_url}/efetch.fcgi"
    papers = []
    sleep_time = 0.4 if not api_key else 0.1  # Rate limiting

    for i, pmid in enumerate(pmids):
        try:
            fetch_params = {
                "db": "pubmed",
                "id": pmid,
                "retmode": "xml"
            }

            if api_key:
                fetch_params["api_key"] = api_key

            response = requests.get(fetch_url, params=fetch_params)
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
                        name += f" {forename.text[0]}."
                    authors.append(name)

            # Extract journal
            journal_elem = article.find(".//Journal/Title")
            journal = journal_elem.text if journal_elem is not None and journal_elem.text else "N/A"

            # Extract year
            year_elem = article.find(".//PubDate/Year")
            if year_elem is None:
                year_elem = article.find(".//PubDate/MedlineDate")
            year = year_elem.text[:4] if year_elem is not None and year_elem.text else "N/A"

            # Extract DOI
            doi_elem = article.find(".//ArticleId[@IdType='doi']")
            doi = doi_elem.text if doi_elem is not None and doi_elem.text else "N/A"

            # Extract abstract
            abstract_parts = article.findall(".//Abstract/AbstractText")
            abstract = " ".join([p.text or "" for p in abstract_parts if p.text])
            if not abstract:
                abstract = "No abstract available"

            papers.append({
                "PMID": pmid,
                "Title": title,
                "Authors": "; ".join(authors[:5]) + (" et al." if len(authors) > 5 else ""),
                "Year": year,
                "Journal": journal,
                "DOI": doi,
                "Abstract": abstract,
                "URL": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            })

            print(f"  [{i+1}/{len(pmids)}] {title[:60]}...")

            # Rate limiting
            time.sleep(sleep_time)

        except Exception as e:
            print(f"  Error processing PMID {pmid}: {e}")
            continue

    return papers


def save_to_csv(papers, filename="pubmed_results.csv"):
    """Save papers to CSV file"""
    if not papers:
        print("No papers to save.")
        return

    fieldnames = ["PMID", "Title", "Authors", "Year", "Journal", "DOI", "Abstract", "URL"]
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(papers)

    print(f"\nSaved {len(papers)} papers to {filename}")


def generate_citations(papers, format_type="gbt", output_file="citations.txt"):
    """
    Generate citations in various formats

    format_type:
    - "gbt": GB/T 7714 (Chinese standard)
    - "vancouver": Vancouver style
    - "apa": APA style
    """
    citations = []

    for i, paper in enumerate(papers, 1):
        authors = paper["Authors"].split("; ")[0]  # First author
        title = paper["Title"]
        journal = paper["Journal"]
        year = paper["Year"]
        doi = paper["DOI"]

        if format_type == "gbt":
            # GB/T 7714 format
            citation = f"[{i}] {authors}. {title}[J]. {journal}, {year}. DOI: {doi}"
        elif format_type == "vancouver":
            # Vancouver format
            citation = f"{i}. {authors}. {title}. {journal}. {year}. doi: {doi}"
        elif format_type == "apa":
            # APA format
            citation = f"{authors} ({year}). {title}. {journal}. https://doi.org/{doi}"
        else:
            citation = f"{i}. {authors}. {title}. {journal}, {year}."

        citations.append(citation)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n\n".join(citations))

    print(f"Generated {len(citations)} citations in {format_type} format -> {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search PubMed for academic literature")
    parser.add_argument("query", help="Search query (use quotes for complex queries)")
    parser.add_argument("-n", "--num", type=int, default=50, help="Number of results (default: 50)")
    parser.add_argument("-y", "--years", type=int, default=5, help="Years to look back (default: 5)")
    parser.add_argument("-t", "--type", help="Article type filter (e.g., 'Clinical Trial', 'Review')")
    parser.add_argument("-o", "--output", default="pubmed_results.csv", help="Output CSV filename")
    parser.add_argument("-c", "--citations", help="Generate citations (format: gbt/vancouver/apa)")
    parser.add_argument("--api-key", help="NCBI API key for faster requests")

    args = parser.parse_args()

    # Search PubMed
    papers = search_pubmed(
        query=args.query,
        max_results=args.num,
        years=args.years,
        article_type=args.type,
        api_key=args.api_key or NCBI_API_KEY
    )

    # Save results
    if papers:
        save_to_csv(papers, args.output)

        # Generate citations if requested
        if args.citations:
            generate_citations(papers, format_type=args.citations)
