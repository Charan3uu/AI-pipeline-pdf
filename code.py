import fitz
import pdfplumber
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Get text from pdf
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text


def extract_tables_from_pdf(pdf_path):  # tables extracton
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            for table in page.extract_tables():
                tables.append({
                    "page": page_idx + 1,
                    "data": table
                })
    return tables



def split_into_sections(text):       # split to sections 
    section_titles = [
        "abstract", "introduction", "background",
        "methodology", "methods",
        "experiments", "experimental setup",
        "results", "evaluation",
        "discussion", "conclusion", "references"
    ]

    sections = {}
    current = "unknown"
    sections[current] = ""

    for line in text.split("\n"):
        clean = line.strip().lower()

        for title in section_titles:
            if clean == title or clean.startswith(title):
                current = title
                sections[current] = ""
                break

        sections[current] += line + " "

    return sections



def tables_to_text(tables):   
    """
    Converts tables into readable text for LLM context
    """
    if not tables:
        return ""

    table_text = "\n\n[TABLES]\n"
    for idx, table in enumerate(tables, 1):
        table_text += f"\nTable {idx} (Page {table['page']}):\n"
        for row in table["data"]:
            table_text += " | ".join(str(cell) for cell in row) + "\n"
    return table_text



def build_context(sections, tables):
    context = ""

    for sec, text in sections.items():
        context += f"\n\n[{sec.upper()}]\n{text}"

    context += tables_to_text(tables)
    return context



def summarize_text(context, focus=None):            # If this code fails then sorry! I dont have any llm api key to test.
    
    focus_text = f"Focus especially on {focus}." if focus else ""

    prompt = f"""
Summarize the following academic content clearly and accurately.
{focus_text}

Include important findings, methods, and quantitative results if present.

Content:
{context}
"""
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return response.choices[0].message.content


def ask_question(question, context):
    prompt = f"""
Answer the question using ONLY the context below.
If numbers or metrics are present, report them exactly.

Context:
{context}

Question:
{question}
"""
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    return response.choices[0].message.content



def process_pdfs(pdf_paths):
    docs = {}

    for pdf in pdf_paths:
        print(f"\nProcessing: {pdf}")

        text = extract_text_from_pdf(pdf)
        tables = extract_tables_from_pdf(pdf)
        sections = split_into_sections(text)

        context = build_context(sections, tables)

        docs[pdf] = {
            "sections": sections,
            "tables": tables,
            "context": context
        }

    return docs


def interactive_session(docs):
    while True:
        q = input("\nAsk a question or type ex to exit: ")
        if q.lower() == "ex":
            break

        combined_context = ""
        for pdf, doc in docs.items():
            combined_context += f"\n\n===== {pdf} =====\n"
            combined_context += doc["context"]

        answer = ask_question(q, combined_context)
        print("\nAnswer:\n", answer)


if __name__ == "__main__":
    pdfs = input("Enter PDF paths: ").split(",")
    pdfs = [p.strip() for p in pdfs]

    documents = process_pdfs(pdfs)

    print("\n--- AUTO SUMMARIES ---\n")
    for pdf, data in documents.items():
        print(f"\n {pdf}")
        print(
            summarize_text(
                data["context"],
                focus="methodology, results, and best-performing metrics"
            )
        )

    interactive_session(documents)
