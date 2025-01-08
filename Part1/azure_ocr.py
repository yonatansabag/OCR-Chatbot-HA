from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import re

# Azure credentials
endpoint = "https://eastus.api.cognitive.microsoft.com/"
key = "YOUR API KEY"

client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))


def clean_numeric_fields(text):
    """
    Fix numeric fields in the OCR output, combining digits split by '|' or 'l'. Effective mostly for dates
    """
    text = re.sub(r"(\d)[|l]+(\d)", r"\1\2", text) # for 'l' or '|' separators
    text = re.sub(r"(\d{2})\s+(\d{2})\s+(\d{4})", r"\1-\2-\3", text) # for spaced numbers
    return text


def extract_text_from_document(file):
    """
    Extract text from a document with Azure OCR
    """
    poller = client.begin_analyze_document("prebuilt-document", file)
    result = poller.result()

    extracted_text = []
    for page in result.pages:
        for line in page.lines:
            extracted_text.append(line.content)

    # Combine all text
    combined_text = "\n".join(extracted_text)
    # Clean up numeric fields
    cleaned_text = clean_numeric_fields(combined_text)
    return {"text": cleaned_text}


