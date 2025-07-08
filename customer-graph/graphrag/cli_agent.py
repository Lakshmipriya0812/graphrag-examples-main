import os
import asyncio

from dotenv import load_dotenv
from semantic_kernel import Kernel
from langchain_community.llms import HuggingFaceHub

from semantic_kernel.contents.chat_history import ChatHistory
from retail_plugin import RetailPlugin
from retail_service import RetailService
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.functions.kernel_arguments import KernelArguments
import logging


logging.basicConfig(level=logging.INFO)

#get info from environment
load_dotenv()
NEO4J_URI=os.getenv('NEO4J_URI')
NEO4J_USER=os.getenv('NEO4J_USERNAME')
NEO4J_PASSWORD=os.getenv('NEO4J_PASSWORD')
service_id = "retail_search"

# Initialize the kernel
kernel = Kernel()

# Add the Contract Search plugin to the kernel
retail_analysis_neo4j = RetailService(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
kernel.add_plugin(RetailPlugin(retail_service=retail_analysis_neo4j), plugin_name="retail_analysis")

hf_llm = HuggingFaceHub(repo_id="google/flan-t5-base")
kernel.hf_llm = hf_llm  # Attach for downstream use


# Create a history of the conversation
history = ChatHistory()

async def basic_agent() :
    userInput = None
    while True:
        # Collect user input
        userInput = input("User > ")

        # Terminate the loop if the user says "exit"
        if userInput == "exit":
            break

        # Add user input to the history
        history.add_user_message(userInput)

        # 3. Get the response from the Hugging Face LLM
        hf_llm = kernel.hf_llm
        result = (await hf_llm.invoke(userInput))

        # Print the results
        print("Assistant > " + str(result))
        print("=============================\n\n")

        # Add the message from the agent to the chat history
        history.add_message(result)

if __name__ == "__main__":
    
    asyncio.run(basic_agent())


    
