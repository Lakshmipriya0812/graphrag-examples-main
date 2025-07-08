import asyncio, os
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import CharacterTextSplitter
from neo4j import GraphDatabase
from neo4j_graphrag.embeddings import SentenceTransformerEmbeddings
from neo4j_graphrag.experimental.components.pdf_loader import DataLoader
from neo4j_graphrag.experimental.components.text_splitters.langchain import LangChainTextSplitterAdapter
from neo4j_graphrag.experimental.components.types import PdfDocument, DocumentInfo
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline
from rag_schema_from_onto import getSchemaFromOnto
from neo4j_graphrag.llm.base import LLMInterface, LLMResponse

#Change to HuggingFaceLLM from OpenAI LLM
try:
    from neo4j_graphrag.llm.huggingface_llm import HuggingFaceLLM
    llm = HuggingFaceLLM(
        model_name="HuggingFaceH4/zephyr-7b-beta",
        model_params={
            "temperature": 0,
            "max_new_tokens": 512,
        },
    )
except ImportError:
    class MockLLM(LLMInterface):
        def __init__(self, model_name="mock-llm"):
            super().__init__(model_name=model_name)
        def __call__(self, prompt, **kwargs):
            return LLMResponse(content="Mock response")
        def invoke(self, prompt, **kwargs):
            return LLMResponse(content="Mock response")
        async def ainvoke(self, prompt, **kwargs):
            return LLMResponse(content="Mock response")
    llm = MockLLM()

load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# Connect to the Neo4j database
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

neo4j_schema = getSchemaFromOnto("ontos/customer.ttl")
print(neo4j_schema)

# Create DocumentLoader
class PdfLoaderWithPageBreaks(DataLoader):
    async def run(self, filepath: Path) -> PdfDocument:
        loader = PyPDFLoader(filepath)
        text = ''
        async for page in loader.alazy_load():
            text = text + " __PAGE__BREAK__ " + page.page_content
        return PdfDocument(
            text=text,
            document_info=DocumentInfo(path=filepath), )

# Create a Splitter object
splitter = LangChainTextSplitterAdapter(
    CharacterTextSplitter(chunk_size=15_000, chunk_overlap=0, separator=" __PAGE__BREAK__ ")
)

# Create an Embedder object
embedder = SentenceTransformerEmbeddings(model="sentence-transformers/all-MiniLM-L6-v2")

# instantiate the SimpleKGPipeline
kg_builder = SimpleKGPipeline(
    llm=llm,
    driver=driver,
    pdf_loader=PdfLoaderWithPageBreaks(),
    text_splitter=splitter,
    embedder=embedder,
    entities=[node.label for node in neo4j_schema.node_types],
    relations=[rel.label for rel in neo4j_schema.relationship_types],
    potential_schema=list(neo4j_schema.patterns),
    on_error="IGNORE",
    from_pdf=True,
)

# load credit notes
asyncio.run(kg_builder.run_async(file_path='data/credit-notes.pdf'))

# perform entity resolution
print("Performing Additional Entity Resolution")
driver.execute_query('''
MATCH (n:Article)
WITH n.articleId AS id, collect(n) as nodes
CALL apoc.refactor.mergeNodes(nodes, {
  properties: {
      `.*`: 'combine'
  },
  mergeRels: true
})
YIELD node
RETURN node;
''')

driver.execute_query('''
MATCH (n:Order)
WITH n.orderId AS id, collect(n) as nodes
CALL apoc.refactor.mergeNodes(nodes, {
  properties: {
      `.*`: 'combine'
  },
  mergeRels: true
})
YIELD node
RETURN node
''')

print("Removing Unneeded Nodes")
driver.execute_query('MATCH (n:Product) WHERE n:__Entity__ DETACH DELETE n')

driver.close()
