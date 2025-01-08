# OCR-Chatbot-HA

This repository contains two main parts:

- **Part1**: Contains scripts related to OCR and GPT functionalities.
- **Part2**: Contains a chatbot application that utilizes OCR and GPT for processing and responding to user queries.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/yonatansabag/OCR-Chatbot-HA.git
   cd OCR-Chatbot-HA
   ```
   
2. **Install Dependencies:**
   
   Ensure you're in the root directory of the repository where the requirements.txt file is located.
   
   ```bash
   pip install -r requirements.txt
   ```
## Running the Applications

### Part1
Part 1 focuses on OCR functionalities integrated with a LLM
1. **Navigate to the Part1 Directory:**
   
   ```bash
   cd Part1
   ```
2. **Run the Desired Script:**
   To run the OCR application:
   
   ```bash
   python main.py
   ```

### Part2
Part 2 focuse on creating a microservice-based chatbot system.

1. **Navigate to the Part2 Directory:**

   ```bash
   cd ../Part2 
   ```

  If coming from Part1 directory.
  
  or
  
   ```bash
   cd Part2 
   ```

  If coming from main directory.

2. **Generate Knowledge Base:**

   Before running the application, generate the knowledge base by executing:
   
   ```bash
   python generate_kb.py
   ```

4. **Start the Backend Server:**

   Run the FastAPI backend using Uvicorn:

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

5. **Start the Frontend Application:**

   In a separate terminal, run the frontend application:

   ```bash
   python app/frontend.py
   ```   

6. **Open the App in the Browser:**

   After starting the frontend (python app/frontend.py), navigate to the following URL in your browser:

   - ***Local Access***: http://127.0.0.1:7860
     
   
