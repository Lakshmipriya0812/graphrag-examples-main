import os

from dotenv import load_dotenv
from neo4j import GraphDatabase
from langchain_community.embeddings import HuggingFaceEmbeddings

load_dotenv()
NEO4J_URI=os.getenv("NEO4J_URI")
NEO4J_USERNAME=os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD=os.getenv("NEO4J_PASSWORD")



# Connect to the Neo4j database
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

# create text properties for product
print("Formatting Product Text")
driver.execute_query('''
MATCH(p:Product)
OPTIONAL MATCH(p)-[:PART_OF]->(c:ProductCategory)
OPTIONAL MATCH(p)-[:PART_OF]->(t:ProductType)
SET p.text = '##Product\n' +
    'Name: ' + coalesce(p.name,'') + '\n' +
    'Type: ' + coalesce(t.name, '') + '\n' +
    'Category: ' + coalesce(c.name, '') + '\n' +
    'Description: ' + coalesce(p.description, ''),
    p.url = 'https://representative-domain/product/' + p.productCode
RETURN count(p) AS propertySetCount
''')

# create text embeddings for products using Hugging Face
print("Creating Product Text Embeddings with Hugging Face")
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
with driver.session(database="neo4j") as session:
    # Fetch all products with a description
    result = session.run('''
        MATCH (n:Product) WHERE size(n.description) <> 0 RETURN id(n) as node_id, n.text as text
    ''')
    products = list(result)
    print(f"Found {len(products)} products to embed.")
    for product in products:
        node_id = product["node_id"]
        text = product["text"]
        if not text:
            continue
        embedding = embedding_model.embed_documents([text])[0]
        # Store the embedding as a property on the node
        session.run(
            """
            MATCH (n) WHERE id(n) = $node_id
            SET n.textEmbedding = $embedding
            """,
            node_id=node_id,
            embedding=embedding
        )

# create vector index on text embeddings
print("Creating Product Vector Index")
driver.execute_query('''
CREATE VECTOR INDEX product_text_embeddings IF NOT EXISTS FOR (n:Product) ON (n.textEmbedding)
OPTIONS {indexConfig: {
 `vector.dimensions`: toInteger($dimension),
 `vector.similarity_function`: 'cosine'
}}
''', dimension=1536)

# wait for index to come online
driver.execute_query('CALL db.awaitIndex("product_text_embeddings", 300)')


driver.close()

