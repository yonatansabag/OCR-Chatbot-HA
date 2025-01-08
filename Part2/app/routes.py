from fastapi import APIRouter, HTTPException
from langdetect import detect
from openai import AsyncAzureOpenAI
from app.utils import find_closest_match
import logging
import json
import asyncio
import re
from uuid import UUID

router = APIRouter()

# Get logger
logger = logging.getLogger("chatbot")

# Get AzureOpenAi client
client = AsyncAzureOpenAI(
    api_version="2023-07-01-preview",
    azure_endpoint="https://<your-endpoint>.openai.azure.com/",
    api_key="<your-azure-openai-api-key>"
)

# Load precomputed knowledge base embeddings
with open("knowledge_base_embeddings_chunked.json", "r", encoding="utf-8") as kb_file:
    knowledge_base = json.load(kb_file)
    logger.info("Knowledge base was loaded.")


@router.post("/collect_user_info")
async def collect_user_info(conversation_history: dict):
    """
    Collect and process user information dynamically using LLM prompts.

    Args:
        conversation_history (dict): 
            A dictionary containing the current conversation state. 
            Keys:
                - session_id (str): Unique identifier for the user session.
                - user_input (str): User's latest input message.
                - previous_gpt_output (str): Previous GPT response in the conversation.
                - collected_data (dict): User data collected so far.
                - confirmation_status (bool): Whether the user has confirmed their details.

    Returns:
        dict: 
            A dictionary containing:
                - status (str): The status of the operation ("success", "pending", or "error").
                - response (str): Message to the user.
                - collected_data (dict): Updated user information.
                - transition_to_qa (bool): Whether to transition to the Q&A phase.

    Raises:
        HTTPException: 
            - 400 if session_id is missing or invalid.
            - 500 for any internal server error.
    """
    logger.info("Received request to collect user information.")
    try:
        session_id = conversation_history.get("session_id")
        if not session_id:
            logger.warning("Session ID is missing in the request.")
            raise HTTPException(status_code=400, detail="Session ID is required.")

        
        logger.info(f"Processing session with ID: {session_id}")
        logging.info(f"Received conversation history: {conversation_history}")
        validate_session_id(session_id)
        # Extract current state
        user_input = conversation_history.get("user_input", "")
        previous_gpt_output = conversation_history.get("previous_gpt_output", "")
        collected_data = conversation_history.get("collected_data", {})
        confirmation_status = conversation_history.get("confirmation_status", False)
        
        # Validate collected data
        logging.info(f"Current collected data: {collected_data}")

        # Define required fields
        required_fields = [
            "first_name",
            "last_name",
            "id_number",
            "gender",
            "age",
            "hmo_name",
            "insurance_membership_tier",
            "hmo_card_number",
        ]

        # Check if all required fields are collected
        missing_fields = [
            field for field in required_fields
            if field not in collected_data or not collected_data[field]
        ]

        logger.info(f"Missing fields: {missing_fields}")
        # Construct the GPT prompt
        if missing_fields:
            prompt = f"""
            You are a helpful assistant who is very proficient in Hebrew and in English, tasked with collecting user information for the following fields:
            - first_name
            - last_name
            - id_number (9-digit number)
            - gender
            - age (between 0 and 120)
            - hmo_name (מכבי=maccabi, כללית=clalit, מאוחדת=meuhedet)
            - hmo_card_number (9-digit number)
            - insurance_membership_tier (זהב=gold, כסף=silver, ארד=bronze)

            Always use these exact keys when returning your response.
            
            Current collected data: {collected_data}

            User input: "{user_input}"
            Assistant's previous message: "{previous_gpt_output}"
            Confirmation status: {confirmation_status}
            
            Your response MUST:
            1. Be a valid JSON object. You must escape anything properly.
            2. Include all required keys: "field_to_update", "value", "message_to_user", "confirmation_status", and "transition_to_qa".
            3. Use `null` for the "value" key if the user input is invalid or does not apply.
            4. Escape all newline characters (`\n`) as `\\n`.
            5. Contain no trailing commas.
            6. Be returned as plain text without additional formatting.

            Important considerations:
            - If the user's input for a field is invalid, re-prompt the user with clear instructions in "message_to_user".
            - If the input is valid, include the updated value in "value", and move to the next field.
            - Ensure "field_to_update" reflects the next field to update if any.
            - Avoid returning repetitive or unclear instructions.
            - Avoid returning `null` for valid inputs.
            - If all data is collected, summarize it and ask for confirmation.

            You must respond in the following structured JSON format:
                {{
                    "field_to_update": "<field_name>" (if applicable, otherwise omit or set to null),
                    "value": "<user_input>" (if applicable, otherwise set to null),
                    "message_to_user": "<response for the user in Hebrew if the user is Hebrew speaker, or in English if the user is English speaker>",
                    "confirmation_status": <true_or_false>,
                    "transition_to_qa": <true_or_false>
                }}
            """
        else:
            # All fields are collected, ask for confirmation
            prompt = f"""
            All required information has been collected:
            {collected_data}
            
            User input: "{user_input}"
            Assistant's previous message: "{previous_gpt_output}"
            Confirmation status: {confirmation_status}
            
            Ask the user to confirm the above information. Recognize confirmation with any of these inputs:
            - In Hebrew: "כן", "אני מאשר", "הכל בסדר", "מאושר", "אכן" 
            - In English: "yes", "correct", "all good", "confirmed"
            
            If the user confirms, set `confirmation_status` to `true` and `transition_to_qa` to `true`.
            If the user denies or provides corrections:
            - Set `confirmation_status` to `false`.
            - Ask which field needs to be corrected.
            - You must accept the correction if its valid and update the relevant field in the collected data.
            - After the correction, you must confirm the updated information and ask for final confirmation

            Respond in the following structured JSON format:
            {{
                "confirmation_status": <true_or_false>,
                "message_to_user": "<response in Hebrew or English>",
                "transition_to_qa": <true_or_false>
            }}
            
            Special Considerations:
            - Your response MUST be a valid JSON string.
            - Do NOT include raw newline characters (\n) unless escaped.
            - You must recognize above inputs as confirmation only when the user asked before if all of his data is correct. 
            """
        
        logger.info("Sending prompt to GPT.")  
        # Send the prompt to GPT
        gpt_response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
            ],
        )

        logger.info("Received response from GPT.")
        gpt_response_text = gpt_response.choices[0].message.content.strip()
        

        try:
            gpt_response_data = json.loads(gpt_response_text)
            logger.debug(f"GPT response parsed successfully: {gpt_response_data}")
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding GPT response: {e}")
            return {
                "status": "error",
                "response": "There was an issue processing your input. Please try again.",
                "collected_data": collected_data,
            }
            
        required_keys = ["confirmation_status", "message_to_user", "transition_to_qa"]
        if not all(key in gpt_response_data for key in required_keys):
            logging.error(f"Invalid GPT response structure: {gpt_response_data}")
            return {
                "status": "error",
                "response": "An unexpected issue occurred. Please try again.",
                "collected_data": collected_data,
            }

        # Update collected data dynamically
        field_to_update = gpt_response_data.get("field_to_update")
        value = gpt_response_data.get("value")

        if missing_fields:
            if value is None or not value.strip():
                logging.warning(f"Received null value for {field_to_update}. Re-prompting user.")
                return {
                    "status": "pending",
                    "response": gpt_response_data.get(
                        "message_to_user", "Invalid input. Please provide the required information."
                    ),
                    "collected_data": collected_data,
                }
            
        # Handle validation
        if value:
            value = value.strip()
            validation_error = validate_field(field_to_update, value)
            if validation_error:
                logger.warning(f"Validation failed for field '{field_to_update}': {validation_error}")
                return {
                    "status": "pending",
                    "response": f"{validation_error} Please try again.",
                    "collected_data": collected_data,
                }

            # Update the field if validation passes
            collected_data[field_to_update] = value
            logging.info(f"Updated {field_to_update} with value: {value}")
        
        new_confirmation_status = gpt_response_data.get("confirmation_status", confirmation_status)
        transition_to_qa = gpt_response_data.get("transition_to_qa", False)
        
        logger.info(f"Transition to Q&A: {transition_to_qa}, Confirmation Status: {confirmation_status}")
        # Check if transition is valid
        if transition_to_qa and not new_confirmation_status:
            # Prevent transitioning to Q&A if confirmation hasn't been explicitly set
            transition_to_qa = False
            
        # Update confirmation status
        confirmation_status = new_confirmation_status
        
        # Return response
        if transition_to_qa:
            logger.info("Transitioning to Q&A phase.")
            return {
                "status": "success",
                "response": "Thank you for confirming! You can now ask questions.",
                "collected_data": collected_data,
                "transition_to_qa": True,
            }
        else:
            logger.info("Continuing information collection.")
            return {
                "status": "success",
                "response": gpt_response_data.get("message_to_user", ""),
                "collected_data": collected_data,
                "confirmation_status": confirmation_status,
                "transition_to_qa": transition_to_qa,
            }
       
    except Exception as e:
        logging.error(f"Error in collect_user_info: {str(e)}")
        return {
            "status": "error",
            "response": "An internal error occurred. Please try again later.",
            "collected_data": collected_data,
        }

    

@router.post("/answer_query")
async def answer_query(query_data: dict):
    """
    Process a user query and return the most relevant answer.

    Args:
        query_data (dict): 
            A dictionary containing the user query and related user information. 
            Keys:
                - user_info (dict): Information about the user, including HMO details.
                - question (str): The user's query.

    Returns:
        dict: 
            A dictionary containing:
                - status (str): The status of the operation ("success" or "error").
                - closest_match (list): The most relevant knowledge base matches.
                - answer (str): The generated response to the user's query.

    Raises:
        HTTPException: 
            - 400 if required keys (user_info or question) are missing.
            - 404 if no relevant information is found in the knowledge base.
            - 500 for any internal server error.
    """
    logger.info("Received request to answer user query.")
    try:
        # Get phase 1 user info
        user_info = query_data.get("user_info")
        # Get user's question
        question = query_data.get("question")

        # Basic validation
        if not user_info or not question:
            logger.warning("User info or question is missing in the request.")
            raise HTTPException(status_code=400, detail="User info and question are required")
        
        # Get relevance info for retrieval from phase 1 user info
        hmo_name = user_info.get("hmo_name")
        membership_tier = user_info.get("insurance_membership_tier")
        logger.info(f"Processing query for user with HMO: {hmo_name} and membership tier : {membership_tier}")
        logger.debug(f"Question: {question}")

        # Generate embeddings for user query
        logger.info("Generating query embedding.")
        response = await client.embeddings.create(
            input=question,
            model="text-embedding-ada-002"
        )
        query_embedding = response.data[0].embedding
        logger.info("Query embedding generated.")
        
        # Find the closest match in the knowledge base, if exists
        logger.info("Searching for closest matches in the knowledge base.")
        closest_matches = find_closest_match(query_embedding=query_embedding, knowledge_base=knowledge_base)
        # If no match is found in the knowledge base
        if not closest_matches:
            logger.warning("No relevant information found in the knowledge base.")
            raise HTTPException(status_code=404, detail="No relevant information found in the knowledge base.")
        
        logger.info(f"Found {len(closest_matches)} relevant matches.")
        
        prompt = r"""
        You are an expert in Israeli healthcare services. Your task is to provide information to user queries, 
        ONLY based on the given context and given relevant user details. The user has the following details:
        - HMO : {hmo_name}
        - Membership Tier : {membership_tier}
        
        Here are the contexts found relevant to the user's query:
        {contexts}
        
        User's question: {question}
        
        Provide a helpful and accurate response.
        
        If the user's question is in English, reply in English only, make translations when necessary.
        Else, if the question is in Hebrew, reply in Hebrew only.
        
        You MUST follow the following guidelines:
        1. Replies are based only on the given context. 
        2. If you don't know the answer, or it is not in context, reply that you do not know the answer.
        3. Your responses must be accurate.
        4. Replies are only in Hebrew or English.
        """.format(
            hmo_name=hmo_name,
            membership_tier=membership_tier,
            contexts="\n---\n".join([match['content'] for match in closest_matches]),
            question=question
        )
        
        logger.info("Sending prompt to GPT for answering the query.")
        gpt_response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
            ],
        )
        
        logger.info("Received response from GPT.")
        answer = gpt_response.choices[0].message.content.strip()
        logger.info("Query answered successfully.")

        return {
            "status": "success",
            "closest_match": closest_matches,
            "answer": answer
        }
    except Exception as e:
        logger.error(f"Error in answer_query: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    
def validate_session_id(session_id):
    """
    Validate the format of a session ID.

    Args:
        session_id (str): 
            The session ID to validate. Expected to be a valid UUID string.

    Raises:
        HTTPException: 
            - 400 if the session ID is not a valid UUID format.
    """
    try:
        UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format.")

def validate_field(field_name, value):
    """
    Validate a user-provided field and its value.

    Args:
        field_name (str): 
            The name of the field being validated. Expected values include:
            - "first_name", "last_name", "id_number", "gender", "age",
              "hmo_name", "insurance_membership_tier", "hmo_card_number".
        value (str): 
            The value to validate for the given field.

    Returns:
        str: 
            An error message if the validation fails.
        None: 
            If the validation is successful.
    """
    # Ensure the value is non-empty and properly formatted
    if not value or not str(value).strip():
        return f"{field_name.replace('_', ' ').capitalize()} cannot be empty."

    if field_name == "first_name" or field_name == "last_name":
        # Ensure the name contains only alphabetic characters
        if not value.isalpha():
            return f"{field_name.replace('_', ' ').capitalize()} must contain only alphabetic characters."

    elif field_name == "id_number":
        # Ensure the ID number is exactly 9 digits
        if not re.match(r"^\d{9}$", str(value)):
            return "ID number must be exactly 9 digits."

    elif field_name == "gender":
        # Validate gender options
        valid_genders = ["male", "female", "other", "זכר", "נקבה", "אחר", "Male", "Female", "Other"]
        if value.lower() not in valid_genders:
            return "Gender must be male, female, or other."

    elif field_name == "age":
        try:
            # Ensure age is an integer between 0 and 120
            age = int(value)
            if not (0 <= age <= 120):
                return "Age must be a number between 0 and 120."
        except ValueError:
            return "Age must be a valid number."

    elif field_name == "hmo_name":
        # Validate HMO name
        valid_hmos = ["מכבי", "מאוחדת", "כללית", "maccabi", "meuhedet", "clalit", "Maccabi", "Clalit", "Meuhedet"]
        if str(value).lower() not in valid_hmos:
            return "HMO name must be one of: Maccabi, Meuhedet, Clalit."
        # Validate Insurance Membership Tier
    elif field_name == "insurance_membership_tier":
        valid_tiers = ["זהב", "כסף", "ארד", "gold", "silver", "bronze", "Gold", "Silver", "Bronze"]
        if str(value) not in valid_tiers:
            return "Insurance membership tier must be gold, silver, or bronze."

    elif field_name == "hmo_card_number":
        if not re.match(r"^\d{9}$", str(value)):
            return "HMO card number must be exactly 9 digits."
    return None
