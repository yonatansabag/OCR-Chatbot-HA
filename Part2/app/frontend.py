import gradio as gr
import requests
import uuid

# Backend API URLs
COLLECT_USER_INFO_URL = "http://127.0.0.1:8000/collect_user_info"
ANSWER_QUERY_URL = "http://127.0.0.1:8000/answer_query"


def collect_user_info(user_input, previous_gpt_output, conversation_state):
    """
    Phase 1: Collect user information interactively.

    Args:
        user_input (str): 
            The user's current input message.
        previous_gpt_output (str): 
            The previous response from the GPT assistant.
        conversation_state (dict): 
            The current state of the conversation, including:
                - `user_info` (dict): Collected user information.
                - `session_id` (str): Unique identifier for the session.
                - `in_qa_phase` (bool): Flag indicating whether the session is in the Q&A phase.

    Returns:
        tuple: 
            - str: An empty string to clear the user input field.
            - gr.update: Update visibility for the user information collection UI.
            - gr.update: Update visibility for the Q&A phase UI.
            - str: Response message for the user.
            - dict: Updated conversation state.
            - gr.Markdown: Updated progress indicator for the current phase.
    """
    # Prepare the conversation history for the backend
    payload = {
        "user_input": user_input,
        "previous_gpt_output": previous_gpt_output,
        "collected_data": conversation_state.get("user_info", {}),
        "session_id": conversation_state.get("session_id"),
    }

    try:
        # Call the backend to process the input and return the next prompt
        response = requests.post(COLLECT_USER_INFO_URL, json=payload).json()
    except Exception as e:
        return "", gr.update(visible=True), gr.update(visible=False), f"Error: {str(e)}", conversation_state

    # Validate the response structure
    if not isinstance(response, dict) or "collected_data" not in response:
        return "", gr.update(visible=True), gr.update(visible=False), "Error: Invalid response from backend.", conversation_state

    # Update collected data
    conversation_state["user_info"].update(response["collected_data"])

    # Handle transition to Q&A
    if response.get("transition_to_qa", False):
        # Ensure that all required data is collected before transitioning
        required_fields = ["first_name", "last_name", "id_number", "gender", "age", "hmo_name", "hmo_card_number", "insurance_membership_tier"]
        missing_fields = [field for field in required_fields if field not in conversation_state["user_info"]]

        if not missing_fields:
            conversation_state["in_qa_phase"] = True
            progress_html = """
            <div style='display: flex; justify-content: center;'>
                <span style='margin: 0 10px; padding: 5px 10px; background: #ccc; color: #666; border-radius: 5px;'>Step 1: Information Collection</span>
                <span style='margin: 0 10px; padding: 5px 10px; background: #4A90E2; color: white; border-radius: 5px;'>Step 2: Q&A</span>
            </div>
            """
            return (
                "",
                gr.update(visible=False),
                gr.update(visible=True),
                "All information collected successfully! You can now proceed to the Q&A phase.",
                conversation_state,
                gr.Markdown(progress_html),
            )
        else:
            progress_html = """
            <div style='display: flex; justify-content: center;'>
                <span style='margin: 0 10px; padding: 5px 10px; background: #4A90E2; color: white; border-radius: 5px;'>Step 1: Information Collection</span>
                <span style='margin: 0 10px; padding: 5px 10px; background: #ccc; color: #666; border-radius: 5px;'>Step 2: Q&A</span>
            </div>
            """
            return (
                "",
                gr.update(visible=True),
                gr.update(visible=False),
                f"Error: Missing fields detected ({', '.join(missing_fields)}). Please complete all fields.",
                conversation_state,
                gr.Markdown(progress_html),
            )

    # Continue collecting information - maintain Step 1 as active
    progress_html = """
    <div style='display: flex; justify-content: center;'>
        <span style='margin: 0 10px; padding: 5px 10px; background: #4A90E2; color: white; border-radius: 5px;'>Step 1: Information Collection - שלב 1: איסוף מידע</span>
        <span style='margin: 0 10px; padding: 5px 10px; background: #ccc; color: #666; border-radius: 5px;'>Step 2: Q&A - שלב 2: מענה על שאלות</span>
    </div>
    """
    return (
        "",
        gr.update(visible=True),
        gr.update(visible=False),
        response.get("response", "Error: No response received."),
        conversation_state,
        gr.Markdown(progress_html),
    )


def answer_query(question, conversation_state):
    """
    Phase 2: Process a user query based on the collected user information.

    Args:
        question (str): 
            The user's query to be processed.
        conversation_state (dict): 
            The current state of the conversation, including:
                - `user_info` (dict): Collected user information.
                - `session_id` (str): Unique identifier for the session.
                - `conversation_history` (list): History of user queries and responses.

    Returns:
        tuple:
            - str: An empty string to clear the input field.
            - str: The assistant's response to the query.
    """
    # Prepare payload for the backend
    payload = {
        "user_info": conversation_state["user_info"],
        "question": question,
        "session_id": conversation_state["session_id"],  # Include session ID
    }

    # Call the backend
    response = requests.post(ANSWER_QUERY_URL, json=payload).json()

    # Add the query and response to the conversation history
    conversation_state["conversation_history"].append({"query": question, "response": response["answer"]})

    # Return the backend's answer and clear the input
    return "", response["answer"]


def initialize_conversation():
    """
    Initialize a new conversation session.

    Returns:
        tuple: 
            - session_id (str): A unique identifier for the session.
            - dict: A dictionary containing the initial conversation state, including:
                - `user_info` (dict): Placeholder for user-provided information.
                - `conversation_history` (list): Empty list to store conversation exchanges.
                - `session_id` (str): The unique session identifier.
                - `in_qa_phase` (bool): Flag indicating whether the session is in the Q&A phase.
    """
    session_id = str(uuid.uuid4())
    return session_id, {"user_info": {}, "conversation_history": [], "session_id": session_id, "in_qa_phase": False}


# Improved Gradio Interface
def gradio_ui():
    """
    Define and initialize the Gradio-based UI for the chatbot.

    Returns:
        gr.Blocks: 
            A Gradio Blocks interface for the chatbot, including both information collection and Q&A phases.

    UI Features:
        - **Phase 1: User Information Collection**:
            - Text input for user-provided details.
            - Assistant response box for dynamic prompts.
            - Submit button for progressing through the information collection phase.
        - **Phase 2: Question and Answer (Q&A)**:
            - Text input for user questions.
            - Output box for assistant responses.
            - Ask button for submitting questions.
        - Dynamic state management:
            - `session_id` and `conversation_state` are managed via Gradio's `State`.
        - Progress indicators for UI phases:
            - Displays progress from "Information Collection" to "Q&A".
        - Footer section with branding.
    """
    with gr.Blocks() as interface:
        # Title Section
        gr.Markdown(
            """
            <h1 style='text-align: center; color: #4A90E2;'>Medical Services Chatbot - בוט שירותי בריאות</h1>
            <p style='text-align: center;'>A friendly chatbot to assist you in providing your details and answering medical service queries. - זהו צ'אט בוט ידידותי שיעזור לך במענה על שאלות בנושאי שירותי בריאות.</p>
            <hr style="border: 1px solid #4A90E2; width: 80%;">
            """
        )

        # Define states for session and conversation
        session_id = gr.State()
        conversation_state = gr.State()

        # Progress Bar or Step Indicator
        progress_bar = gr.Markdown(
            """
            <div style='display: flex; justify-content: center;'>
                <span style='margin: 0 10px; padding: 5px 10px; background: #4A90E2; color: white; border-radius: 5px;'>Step 1: Information Collection - שלב 1: איסוף מידע</span>
                <span style='margin: 0 10px; padding: 5px 10px; background: #ccc; color: #666; border-radius: 5px;'>Step 2: Q&A - שלב 2: מענה על שאלות</span>
            </div>
            """
        )

        # Phase 1: User Information Collection
        with gr.Row(visible=True) as user_info_phase:
            with gr.Column():
                gr.Markdown(
                    """
                    <h2>Step 1: Provide Your Information - שלב 1: ספק מידע רלוונטי</h2>
                    <p>Please fill in your details below to proceed. - אנא מלא את פרטיך למטה על מנת להמשיך</p>
                    """
                )
                info_input = gr.Textbox(
                    label="Your Input - כתוב כאן",
                    placeholder="E.g., Enter your name, ID number, or other details as requested... - כתוב את שמך הפרטי , תעודת הזהות שלך ועוד, בהתאם לבקשת הבוט..",
                    lines=2,
                )
                assistant_output = gr.Textbox(
                    label="Assistant Response - תשובת הבוט",
                    interactive=False,
                    lines=3,
                    value="Welcome! Please enter your details to get started. - ברוכים הבאים! אנא הכנס את פרטיך על מנת להמשיך, או כתוב הודעת פתיחה כלשהי.",
                )
                submit_button = gr.Button(
                    "Submit - הגש",
                    variant="primary",
                )

        # Phase 2: Q&A
        with gr.Row(visible=False) as qa_phase:
            with gr.Column():
                gr.Markdown(
                    """
                    <h2>Step 2: Ask Your Questions - שלב 2: שאל את שאלותיך</h2>
                    <p>You can now ask questions about medical services. - אתה כעת יכול לשאול שאלות על שירותי בריאות.</p>
                    """
                )
                question_input = gr.Textbox(
                    label="Your Question - השאלה שלך",
                    placeholder="E.g., What services are covered under my HMO? - לדוגמה : איזה שירותים מכוסים בקופת החולים שלי?",
                    lines=2,
                )
                answer_output = gr.Textbox(
                    label="Assistant Answer - תשבות הבוט",
                    interactive=False,
                    lines=4,
                    value="",
                )
                ask_button = gr.Button(
                    "Ask - שאל",
                    variant="primary",
                )
                
        # Backend Initialization
        interface.load(
            fn=initialize_conversation,
            inputs=None,
            outputs=[session_id, conversation_state],
        )

        # Bind button actions
        submit_button.click(
            collect_user_info,
            inputs=[info_input, assistant_output, conversation_state],
            outputs=[
                info_input,                   # Clear user input
                user_info_phase,              # Control user info phase visibility
                qa_phase,                     # Control Q&A phase visibility
                assistant_output,             # Update assistant response
                conversation_state,
                progress_bar,
            ],
        )

        ask_button.click(
            answer_query,
            inputs=[question_input, conversation_state],
            outputs=[question_input, answer_output],  # Clear question input and display answer
        )

        # Add Enter key support for submission
        info_input.submit(
            collect_user_info,
            inputs=[info_input, assistant_output, conversation_state],
            outputs=[
                info_input,                   # Clear user input
                user_info_phase,              # Control user info phase visibility
                qa_phase,                     # Control Q&A phase visibility
                assistant_output,             # Update assistant response
                conversation_state,
                progress_bar,
            ],
        )

        question_input.submit(
            answer_query,
            inputs=[question_input, conversation_state],
            outputs=[question_input, answer_output],  # Clear question input and display answer
        )


    return interface


# Run the Gradio app
if __name__ == "__main__":
    ui = gradio_ui()
    ui.launch()
