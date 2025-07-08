import asyncio, os
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import CharacterTextSplitter
from neo4j import GraphDatabase
from neo4j_graphrag.experimental.components.pdf_loader import DataLoader
from neo4j_graphrag.experimental.components.text_splitters.langchain import LangChainTextSplitterAdapter
from neo4j_graphrag.experimental.components.types import PdfDocument, DocumentInfo
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline
from rag_schema_from_onto import getSchemaFromOnto

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

# Create an Embedder object using neo4j_graphrag's own class
try:
    from neo4j_graphrag.embeddings import SentenceTransformerEmbeddings
    embedder = SentenceTransformerEmbeddings("sentence-transformers/all-MiniLM-L6-v2")
except ImportError:
    # Check what's available
    import neo4j_graphrag.embeddings as embeddings
    print("Available in neo4j_graphrag.embeddings:", dir(embeddings))
    # Fallback to using LangChain embeddings
    from langchain_community.embeddings import HuggingFaceEmbeddings
    embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Instantiate the LLM using neo4j_graphrag's own class
try:
    from neo4j_graphrag.llm import OllamaLLM
    llm = OllamaLLM(model_name="llama2")  # or try without LLM
except ImportError:
    # Check what's available
    import neo4j_graphrag.llm as llm_module
    print("Available in neo4j_graphrag.llm:", dir(llm_module))
    # Create a simple mock LLM that implements the interface
    from neo4j_graphrag.llm import LLMInterface
    class MockLLM(LLMInterface):
        def invoke(self, prompt: str, **kwargs):
            return "Mock response for testing"
        
        async def ainvoke(self, prompt: str, **kwargs):
            return "Mock response for testing"
        
        def generate(self, prompt: str, **kwargs):
            return "Mock response for testing"
    llm = MockLLM()

# instantiate the SimpleKGPipeline
pipeline_args = {
    "llm": llm,  # Always include LLM since it's required
    "driver": driver,
    "pdf_loader": PdfLoaderWithPageBreaks(),
    "text_splitter": splitter,
    "embedder": embedder,
    "entities": [node.label for node in neo4j_schema.node_types],
    "relations": [
        {
            "type": pattern[1],  # relationship type from pattern
            "source": pattern[0],  # source node from pattern
            "target": pattern[2]   # target node from pattern
        }
        for pattern in neo4j_schema.patterns
    ],
    "potential_schema": list(neo4j_schema.patterns),
    "on_error": "IGNORE",
    "from_pdf": True,
}

kg_builder = SimpleKGPipeline(**pipeline_args)

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
