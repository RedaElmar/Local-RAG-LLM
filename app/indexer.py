"""
Document indexing and retrieval functionality for AI Research Assistant
Handles document processing, vector indexing, and semantic search
"""

import os
from typing import List, Dict, Any
from pathlib import Path

# Import LlamaIndex components
try:
    from llama_index import (
        SimpleDirectoryReader,
        VectorStoreIndex,
        ServiceContext,
        StorageContext,
        load_index_from_storage,
    )
    from llama_index.embeddings import LangchainEmbedding
    from langchain_community.embeddings import HuggingFaceEmbeddings
    LLAMA_INDEX_AVAILABLE = True
except ImportError:
    LLAMA_INDEX_AVAILABLE = False
    print("Warning: LlamaIndex not available. Document indexing will not work.")

DOCS_DIR = os.getenv("DOCS_DIR", "data/docs")
INDEX_DIR = os.getenv("INDEX_DIR", "data/index")

def clean_pdf_filenames(docs_dir):
    """Clean PDF filenames for better indexing"""
    if not os.path.exists(docs_dir):
        return
    
    for fname in os.listdir(docs_dir):
        if fname.lower().endswith('.pdf'):
            new_name = fname.rstrip().replace(' ', '_')
            if new_name != fname:
                old_path = os.path.join(docs_dir, fname)
                new_path = os.path.join(docs_dir, new_name)
                try:
                    os.rename(old_path, new_path)
                    print(f"Renamed: '{fname}' -> '{new_name}'")
                except OSError as e:
                    print(f"Could not rename {fname}: {e}")

def build_index(docs_dir=None, specific_files=None):
    """Build vector index from documents in DOCS_DIR or specific files"""
    if not LLAMA_INDEX_AVAILABLE:
        print("❌ LlamaIndex not available. Cannot build index.")
        return None
    
    # Use provided docs_dir or default
    target_docs_dir = docs_dir or DOCS_DIR
    
    if not os.path.exists(target_docs_dir):
        print(f"❌ Documents directory not found: {target_docs_dir}")
        return None
    
    try:
        # Clean PDF filenames
        clean_pdf_filenames(target_docs_dir)
        
        # Load documents - either all or specific files
        if specific_files:
            print(f"📚 Loading specific documents: {specific_files}")
            docs = []
            for filename in specific_files:
                file_path = os.path.join(target_docs_dir, filename)
                if os.path.exists(file_path):
                    # Load single document
                    single_docs = SimpleDirectoryReader(input_files=[file_path]).load_data()
                    docs.extend(single_docs)
                else:
                    print(f"⚠️ File not found: {filename}")
        else:
            print(f"📚 Loading all documents from {target_docs_dir}...")
            docs = SimpleDirectoryReader(target_docs_dir).load_data()
        
        if not docs:
            print("❌ No documents found")
            return None
        
        print(f"✅ Loaded {len(docs)} documents")
        
        # Process document metadata
        for doc in docs:
            # Try to get the filename from file_path, fallback to doc_id, fallback to any known metadata
            filename = None
            if hasattr(doc, "file_path") and doc.file_path:
                filename = os.path.basename(doc.file_path)
            elif "file_path" in doc.metadata and doc.metadata["file_path"]:
                filename = os.path.basename(doc.metadata["file_path"])
            elif "file_name" in doc.metadata and doc.metadata["file_name"]:
                filename = doc.metadata["file_name"]
            # fallback to doc_id if nothing else
            if not filename and hasattr(doc, "doc_id"):
                filename = str(doc.doc_id)
            doc.metadata["source"] = filename or "Unknown"
        
        # Set up embedding model
        print("🔧 Setting up embedding model...")
        
        # Suppress the device info message
        import logging
        logging.getLogger("sentence_transformers.SentenceTransformer").setLevel(logging.WARNING)
        
        # Explicitly specify device
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"📱 Using device: {device}")
        
        embed_model = LangchainEmbedding(
            HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={"device": device}
            )
        )
        service_context = ServiceContext.from_defaults(embed_model=embed_model, llm=None)
        
        # Create and persist index
        print("🏗️ Building vector index...")
        index = VectorStoreIndex.from_documents(docs, service_context=service_context)
        
        # Ensure index directory exists
        os.makedirs(INDEX_DIR, exist_ok=True)
        
        # Persist index
        index.storage_context.persist(INDEX_DIR)
        print(f"✅ Vector index built and persisted → {INDEX_DIR}")
        
        return index
        
    except Exception as e:
        print(f"❌ Error building index: {e}")
        import traceback
        traceback.print_exc()
        return None

def remove_document_from_index(filename):
    """Remove a specific document from the index"""
    if not LLAMA_INDEX_AVAILABLE:
        print("❌ LlamaIndex not available. Cannot remove document from index.")
        return False
    
    try:
        print(f"🗑️ Removing document '{filename}' from index...")
        
        # Get the current index
        index = get_index()
        if not index:
            print("❌ No index available for document removal")
            return False
        
        # For now, we'll rebuild the index without the specific file
        # This is a simple approach - in production you might want more sophisticated removal
        print(f"🔄 Rebuilding index without '{filename}'...")
        
        # Get list of all files except the one to remove
        all_files = []
        for fname in os.listdir(DOCS_DIR):
            if fname != filename and fname.lower().endswith(('.pdf', '.txt', '.md', '.docx')):
                all_files.append(fname)
        
        if not all_files:
            print("⚠️ No files left after removal, clearing index")
            # Clear the index directory
            import shutil
            if os.path.exists(INDEX_DIR):
                shutil.rmtree(INDEX_DIR)
            return True
        
        # Rebuild index with remaining files
        print(f"📚 Rebuilding index with {len(all_files)} remaining files...")
        build_index()
        
        print(f"✅ Successfully removed '{filename}' from index")
        return True
        
    except Exception as e:
        print(f"❌ Error removing document from index: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_index():
    """Get the existing index or build a new one if needed"""
    if not LLAMA_INDEX_AVAILABLE:
        print("❌ LlamaIndex not available. Cannot load index.")
        return None
    
    if not os.path.exists(INDEX_DIR):
        print(f"📚 Index not found at {INDEX_DIR}, building new index...")
        return build_index()
    
    try:
        print(f"📚 Loading existing index from {INDEX_DIR}...")
        storage_context = StorageContext.from_defaults(persist_dir=INDEX_DIR)
        # Explicitly specify device
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        embed_model = LangchainEmbedding(
            HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={"device": device}
            )
        )
        service_context = ServiceContext.from_defaults(embed_model=embed_model, llm=None)
        index = load_index_from_storage(storage_context, service_context=service_context)
        print("✅ Index loaded successfully")
        return index
        
    except Exception as e:
        print(f"❌ Error loading index: {e}")
        print("🔄 Rebuilding index...")
        return build_index()

def retrieve(query: str, k: int = 4):
    """Retrieve relevant passages for a query"""
    if not LLAMA_INDEX_AVAILABLE:
        print("❌ LlamaIndex not available. Cannot retrieve documents.")
        return []
    
    try:
        index = get_index()
        if not index:
            print("❌ No index available for retrieval")
            return []
        
        print(f"🔍 Retrieving {k} passages for query: {query[:50]}...")
        passages = index.as_retriever(similarity_top_k=k).retrieve(query)
        print(f"✅ Retrieved {len(passages)} passages")
        return passages
        
    except Exception as e:
        print(f"❌ Error during retrieval: {e}")
        return []

def get_document_info():
    """Get information about available documents"""
    if not os.path.exists(DOCS_DIR):
        return {"error": f"Documents directory not found: {DOCS_DIR}"}
    
    try:
        files = []
        for fname in os.listdir(DOCS_DIR):
            if fname.lower().endswith(('.pdf', '.txt', '.md', '.docx')):
                file_path = os.path.join(DOCS_DIR, fname)
                file_size = os.path.getsize(file_path)
                files.append({
                    "name": fname,
                    "size": file_size,
                    "size_mb": round(file_size / (1024 * 1024), 2)
                })
        
        return {
            "documents_dir": DOCS_DIR,
            "index_dir": INDEX_DIR,
            "total_files": len(files),
            "files": files
        }
        
    except Exception as e:
        return {"error": f"Error reading documents: {e}"}

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Document indexing and retrieval")
    parser.add_argument("--build", action="store_true", help="Build document index")
    parser.add_argument("--info", action="store_true", help="Show document information")
    parser.add_argument("--query", type=str, help="Test query for retrieval")
    parser.add_argument("--k", type=int, default=4, help="Number of passages to retrieve")
    
    args = parser.parse_args()
    
    if args.build:
        print("🏗️ Building document index...")
        build_index()
    
    if args.info:
        print("📚 Document information:")
        info = get_document_info()
        if "error" in info:
            print(f"❌ {info['error']}")
        else:
            print(f"Directory: {info['documents_dir']}")
            print(f"Total files: {info['total_files']}")
            for file_info in info['files']:
                print(f"  - {file_info['name']} ({file_info['size_mb']} MB)")
    
    if args.query:
        print(f"🔍 Testing retrieval with query: {args.query}")
        passages = retrieve(args.query, args.k)
        print(f"Retrieved {len(passages)} passages:")
        for i, passage in enumerate(passages, 1):
            source = passage.metadata.get("source", "Unknown")
            text_preview = passage.node.text[:100] + "..." if len(passage.node.text) > 100 else passage.node.text
            print(f"  {i}. Source: {source}")
            print(f"     Text: {text_preview}")
            print()
