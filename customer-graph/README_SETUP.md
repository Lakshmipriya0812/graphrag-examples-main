# Customer Graph Setup Guide

## Quick Start

### Option 1: Use the setup script (Recommended)
```bash
cd customer-graph
python setup_and_run.py
```

### Option 2: Manual setup
```bash
cd customer-graph
pip install -r requirements.txt
python unstructured_ingest.py
```

## Environment Variables

Create a `.env` file in the `customer-graph` directory with your Neo4j credentials:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
```

## Troubleshooting

### File Path Errors
If you get "No such file or directory" errors, make sure you're running the script from the `customer-graph` directory.

### Ollama Not Installed
If you don't have Ollama installed, the script will automatically use a mock LLM. To install Ollama:
```bash
pip install ollama
```

### Missing Dependencies
If you encounter import errors, install the required packages:
```bash
pip install python-dotenv langchain-community langchain-text-splitters neo4j sentence-transformers torch transformers PyPDF2 pydantic
```

### Neo4j Connection Issues
- Make sure your Neo4j database is running
- Check that your connection credentials are correct
- Verify that the database is accessible from your current environment

## What the Script Does

1. **Loads the ontology** from `ontos/customer.ttl`
2. **Processes PDF documents** from `data/credit-notes.pdf`
3. **Extracts entities and relationships** using the defined schema
4. **Performs entity resolution** to merge duplicate nodes
5. **Cleans up** unnecessary nodes

## Output

The script will create nodes and relationships in your Neo4j database based on the processed PDF content and the defined ontology schema. 