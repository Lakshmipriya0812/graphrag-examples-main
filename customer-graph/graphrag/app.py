import streamlit as st
import os
import asyncio

from dotenv import load_dotenv
from semantic_kernel import Kernel
from semantic_kernel.contents.chat_history import ChatHistory
from retail_plugin import RetailPlugin
from retail_service import RetailService
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.functions.kernel_arguments import KernelArguments
import logging
import time
from langchain_community.llms import HuggingFaceHub

# Configure logging
logging.basicConfig(level=logging.INFO)

# Get info from environment
load_dotenv('../.env')
NEO4J_URI = os.getenv('NEO4J_URI')
NEO4J_USER = os.getenv('NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')
service_id = "contract_search"

# Streamlit app configuration
st.set_page_config(layout="wide")
st.title("📄 Agent for Retail Analytics")

# Initialize Kernel, Chat History, and Settings in Session State
if 'semantic_kernel' not in st.session_state:
    # Initialize the kernel
    kernel = Kernel()

    # Add the Contract Search plugin to the kernel
    retail_analytics_neo4j = RetailService(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    kernel.add_plugin(RetailPlugin(retail_service=retail_analytics_neo4j), plugin_name="retail_analytics")

    # Add the Hugging Face LLM service to the Kernel
    hf_llm = HuggingFaceHub(repo_id="google/flan-t5-base")
    kernel.hf_llm = hf_llm  # Attach for downstream use

    # Create a history of the conversation
    st.session_state.semantic_kernel = kernel
    st.session_state.kernel_settings = None # No longer needed
    st.session_state.chat_history = ChatHistory()
    st.session_state.ui_chat_history = []  # For displaying messages in UI

if 'user_question' not in st.session_state:
    st.session_state.user_question = ""  # To retain the input text value


# Function to get a response from the agent
async def get_agent_response(user_input):
    kernel = st.session_state.semantic_kernel
    history = st.session_state.chat_history
    settings = st.session_state.kernel_settings

    # Add user input to the chat history
    history.add_user_message(user_input)
    st.session_state.ui_chat_history.append({"role": "user", "content": user_input})


    retry_attempts = 3
    for attempt in range(retry_attempts):

    # Get the response from the agent
        try:
            # Use the Hugging Face LLM directly
            hf_llm = kernel.hf_llm
            result = (await hf_llm.invoke(
                user_input,
                #arguments=KernelArguments(),
            ))
            

            # Add the agent's reply to the chat history
            history.add_message(result)
            st.session_state.ui_chat_history.append({"role": "agent", "content": str(result)})
            
            return # Exit after successful response
        
        except Exception as e:
            if attempt < retry_attempts - 1:
                #st.warning(f"Connection error: {str(e)}. Retrying ...")
                time.sleep(0.2)  # Wait before retrying
            else:
                print ("get_agent_response-error" + str(e))
                st.session_state.ui_chat_history.append({"role": "agent", "content": f"Error: {str(e)}"})

# UI for Q&A interaction
st.subheader("Chat with Your Agent")

# Container for chat history
chat_placeholder = st.container()

# Function to display the chat history
def display_chat():
    with chat_placeholder:
        for chat in st.session_state.ui_chat_history:
            if chat['role'] == 'user':
                st.markdown(f"**User:** {chat['content']}")
            else:
                st.markdown(f"**Agent:** {chat['content']}")


# Create a form for the input so that pressing Enter triggers the form submission
with st.form(key="user_input_form"):
    #user_question = st.text_input("Enter your question:", key="user_question")
    user_question = st.text_input("Enter your question:", value=st.session_state.user_question, key="user_question_")
    send_button = st.form_submit_button("Send")

# Execute the response action when the user clicks "Send" or presses Enter
if send_button and user_question.strip() != "":
    # Retain the value of user input in session state to display it in the input box
    st.session_state.user_question = user_question
    # Run the agent response asynchronously in a blocking way
    print(f"Questions: {user_question} ")
    print("---------------------------")
    asyncio.run(get_agent_response(st.session_state.user_question))
    print("=============================\n\n")
    # Clear the session state's question value after submission
    st.session_state.user_question = ""
    display_chat()
    
elif send_button:
    st.error("Please enter a question before sending.")

# Input for user question
#user_question = st.text_input("Enter your question:")



# Button to send the question
#if st.button("Send"):
#    if user_question.strip() != "":
        # Run the agent response asynchronously
#        asyncio.run(get_agent_response(user_question))
#        # Update chat history in UI
#        #display_chat()
#        st.rerun()
#    else:
#        st.error("Please enter a question before sending.")

# Footer
st.markdown("---")
