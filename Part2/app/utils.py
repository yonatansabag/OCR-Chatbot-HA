import logging
from fastapi import HTTPException
from openai import AzureOpenAI
import os
import re
import numpy as np
from bs4 import BeautifulSoup
import json
import numpy as np
from scipy.spatial.distance import cosine
import logging

logger = logging.getLogger("chatbot")

client = AzureOpenAI(
    api_version="2023-07-01-preview",
    azure_endpoint="https://oai-lab-test-eastus-001.openai.azure.com/",
    api_key="47221f36001a4b94839e3cea4365197f"
)


def extract_raw_text(file_path):
    """
    Extract raw text from an HTML file, preserving its structure.

    Args:
        file_path (str): 
            The path to the HTML file to extract text from.

    Returns:
        str: 
            A string containing the extracted text, with headers, paragraphs, lists, and tables preserved.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "lxml")
        text = []

        # Extract headers, paragraphs, and list items
        for tag in soup.find_all(["h2", "h3", "p", "li", "br"]):
            content = tag.get_text(strip=True)
            if content:
                text.append(content)

        # Extract tables row by row
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                row_text = " | ".join(cell.get_text(strip=True) for cell in cells if cell.get_text(strip=True))
                if row_text:
                    text.append(row_text)

        return "\n".join(text)
    
    
def chunk_text(raw_text, max_tokens=150):
    """
    Split raw text into smaller chunks based on a maximum token size.

    Args:
        raw_text (str): 
            The input text to be split into chunks.
        max_tokens (int, optional): 
            The maximum number of tokens allowed per chunk. Default is 150.

    Returns:
        list: 
            A list of text chunks, where each chunk does not exceed the specified token limit.
    """
    chunks = []
    current_chunk = []
    token_count = 0

    for line in raw_text.split("\n"):
        line_tokens = line.split()
        if token_count + len(line_tokens) > max_tokens:
            # Save the current chunk and start a new one
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            token_count = 0
        
        # Add the current line to the chunk
        current_chunk.append(line)
        token_count += len(line_tokens)

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks

    

def generate_embedding(text):
    """
    Generate an embedding for the given text using Azure OpenAI's ADA model.

    Args:
        text (str): 
            The input text for which the embedding is to be generated.

    Returns:
        numpy.ndarray: 
            A NumPy array representing the embedding vector of the input text.
    """
    response = client.embeddings.create(
        input=text,
        model="text-embedding-ada-002"
    )
    return np.array(response.data[0].embedding)



def generate_embeddings_for_html_files_with_chunking(data_dir, output_file="knowledge_base_embeddings_chunked.json", max_tokens=150):
    """
    Generate chunked embeddings for HTML files and save them to a JSON file.

    Args:
        data_dir (str): 
            Path to the directory containing HTML files.
        output_file (str, optional): 
            Path to the JSON file where the embeddings will be saved. Default is "knowledge_base_embeddings_chunked.json".
        max_tokens (int, optional): 
            Maximum number of tokens per chunk. Default is 150.

    Returns:
        None: 
            Saves the generated embeddings and their corresponding text chunks to the specified JSON file.
    """
    logger.info(f"Generating embeddings for files in directory: {data_dir}")
    embeddings = {}
    for file_name in os.listdir(data_dir):
        if file_name.endswith(".html"):
            file_path = os.path.join(data_dir, file_name)
            raw_text = extract_raw_text(file_path)

            # Chunk text intelligently
            chunks = chunk_text(raw_text, max_tokens=max_tokens)
            file_data = []

            for i, chunk in enumerate(chunks):
                # Generate embedding for each chunk
                embedding = generate_embedding(chunk)
                file_data.append({
                    "chunk_id": f"{file_name}_chunk_{i}",
                    "embedding": embedding.tolist(),
                    "content": chunk
                })

            embeddings[file_name] = file_data

    # Save embeddings to a JSON file
    with open(output_file, "w", encoding="utf-8") as json_file:
        json.dump(embeddings, json_file, ensure_ascii=False, indent=4)

    print(f"Chunked embeddings saved to {output_file}")
    
    

def find_closest_match(query_embedding, knowledge_base, threshold=0.3):
    """
    Find the closest matches in the knowledge base for a given query embedding.
    Args:
        query_embedding (np.ndarray): The embedding of the user's query.
        knowledge_base (dict): The precomputed knowledge base containing chunks and their embeddings.
        threshold (float): Distance threshold to consider multiple relevant chunks.

    Returns:
        list: Closest matches within the threshold, sorted by distance.
    """
    matches = []

    for file_name, chunks in knowledge_base.items():
        for chunk in chunks:
            kb_embedding = np.array(chunk["embedding"])
            distance = cosine(query_embedding, kb_embedding)
            if distance <= threshold:
                matches.append({
                    "file": file_name,
                    "chunk_id": chunk["chunk_id"],
                    "content": chunk["content"],
                    "distance": distance
                })

    # Sort matches by distance
    matches = sorted(matches, key=lambda x: x["distance"])
    return matches

