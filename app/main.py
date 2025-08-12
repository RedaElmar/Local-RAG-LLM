from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import os
import shutil
from pathlib import Path
from typing import List
import logging

# Handle imports for both relative and absolute cases
try:
    from .ollama_client import generate
    from .rag import retrieve, run_pipeline, rebuild_index
    from .indexer import build_index, remove_document_from_index
except ImportError:
    # Fallback for when running as standalone
    from ollama_client import generate
    from rag import retrieve, run_pipeline, rebuild_index
    from indexer import build_index, remove_document_from_index

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Local RAG ChatGPT")

# Serve docs as static files at /static/docs
# This allows linking to /static/docs/<filename>
docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/docs'))
print(f"[DEBUG] Mounting /static/docs from: {docs_dir}")
app.mount("/static/docs", StaticFiles(directory=docs_dir), name="docs")

# Serve static files from the frontend directory at /static
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend'))
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

# Serve favicon.ico from the app folder
@app.get('/favicon.ico')
def favicon():
    return FileResponse(os.path.join(os.path.dirname(__file__), 'favicon.png'))

# Serve index.html at root
@app.get("/")
def read_index():
    return FileResponse(os.path.join(frontend_dir, "index.html"))

class ChatRequest(BaseModel):
    query: str
    model: str = "gemma3:4b"  # Default to Gemma 3 4B
    mode: str = "quick"  # Add mode to request

class FileInfo(BaseModel):
    name: str
    size: int
    modified: float  # Changed from str to float for timestamp
    type: str

@app.post("/chat")
async def chat(req: ChatRequest):
    if req.mode == "team":
        result = run_pipeline(req.query, model=req.model)
        return result
    else:
        passages = retrieve(req.query)
        if not passages:
            # If no passages retrieved (e.g., LlamaIndex not available), use direct generation
            sys_prompt = """You are a helpful AI assistant. Provide a clear, direct answer to the user's question.

GUIDELINES:
- Be direct and informative
- Use clear, simple language
- Focus on answering the question asked
- Keep your response reasonable and helpful"""
            
            try:
                answer = generate(
                    req.query, 
                    system_prompt=sys_prompt, 
                    model=req.model,
                    max_tokens=512,   # Reasonable token limit
                    temperature=0.7,  # Balanced temperature
                    top_p=0.9,        # Standard sampling
                    num_predict=512,  # Reasonable prediction limit
                    timeout=60        # 1 minute timeout
                )
                return {
                    "answer": answer,
                    "sources": [],
                    "note": "No document context available - direct response generated",
                    "mode": "quick_direct"
                }
            except Exception as e:
                logger.error(f"Quick mode direct generation failed: {e}")
                return {
                    "answer": f"⚠️ Quick mode generation failed: {str(e)}. Please try team mode for more reliable results.",
                    "sources": [],
                    "note": "Generation failed - fallback message provided",
                    "mode": "quick_direct_failed",
                    "error": str(e)
                }
        else:
            # Limit context length to prevent overwhelming the model
            context_parts = []
            total_chars = 0
            max_context_chars = 2000  # Limit context to 2000 characters
            
            for p in passages:
                if total_chars + len(p.node.text) <= max_context_chars:
                    context_parts.append(p.node.text)
                    total_chars += len(p.node.text)
                else:
                    break
            
            context = "\n".join(context_parts)
            
            sys_prompt = f"""You are a helpful AI assistant. Answer the user's question using the context provided below.

INSTRUCTIONS:
- Use the information from the provided context
- Be clear and informative
- If the context doesn't contain enough information, mention what's available
- Provide a helpful response based on the context

Context:
{context}"""
            
            try:
                answer = generate(
                    req.query, 
                    system_prompt=sys_prompt, 
                    model=req.model,
                    max_tokens=768,   # Reasonable token limit for context-based responses
                    temperature=0.6,  # Balanced temperature
                    top_p=0.9,        # Standard sampling
                    num_predict=768,  # Reasonable prediction limit
                    num_ctx=2048,     # Standard context window
                    timeout=90        # 1.5 minutes timeout
                )
                return {
                    "answer": answer,
                    "sources": [p.metadata.get("source", "Unknown") for p in passages],
                    "mode": "quick_rag",
                    "context_length": len(context),
                    "passages_used": len(context_parts)
                }
            except Exception as e:
                logger.error(f"Quick mode RAG generation failed: {e}")
                return {
                    "answer": f"⚠️ Quick mode generation failed: {str(e)}. Please try team mode for more reliable results.",
                    "sources": [p.metadata.get("source", "Unknown") for p in passages],
                    "note": "Generation failed - fallback message provided",
                    "mode": "quick_rag_failed",
                    "error": str(e),
                    "context_length": len(context),
                    "passages_used": len(context_parts)
                }

# File Management API Endpoints

@app.get("/api/files")
async def list_files():
    """List all files in the docs directory"""
    try:
        files = []
        for file_path in Path(docs_dir).iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append(FileInfo(
                    name=file_path.name,
                    size=stat.st_size,
                    modified=file_path.stat().st_mtime,
                    type=file_path.suffix.lower()
                ))
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x.modified, reverse=True)
        
        return {
            "success": True,
            "files": [file.dict() for file in files],
            "total_count": len(files),
            "total_size": sum(f.size for f in files)
        }
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file to the docs directory and process it into the RAG system"""
    try:
        # Validate file type
        allowed_extensions = {'.pdf', '.txt', '.doc', '.docx', '.md'}
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"File type {file_extension} not allowed. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        # Create docs directory if it doesn't exist
        os.makedirs(docs_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(docs_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process the file into the RAG system
        try:
            logger.info(f"Processing uploaded file: {file.filename}")
            # Add the new document to the index
            build_index(docs_dir=docs_dir, specific_files=[file.filename])
            logger.info(f"Successfully processed file: {file.filename}")
            
            return {
                "success": True,
                "message": f"File {file.filename} uploaded and processed successfully",
                "filename": file.filename,
                "size": os.path.getsize(file_path),
                "processed": True
            }
        except Exception as processing_error:
            logger.error(f"Failed to process file {file.filename}: {processing_error}")
            # File was uploaded but processing failed
            return {
                "success": True,
                "message": f"File {file.filename} uploaded but processing failed: {str(processing_error)}",
                "filename": file.filename,
                "size": os.path.getsize(file_path),
                "processed": False,
                "processing_error": str(processing_error)
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

@app.delete("/api/files/{filename}")
async def delete_file(filename: str):
    """Delete a file from the docs directory and remove it from the RAG index"""
    try:
        file_path = os.path.join(docs_dir, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Remove the document from the RAG index first
        try:
            logger.info(f"Removing document from index: {filename}")
            remove_document_from_index(filename)
            logger.info(f"Successfully removed document from index: {filename}")
        except Exception as index_error:
            logger.warning(f"Failed to remove document from index {filename}: {index_error}")
            # Continue with file deletion even if index removal fails
        
        # Delete the physical file
        os.remove(file_path)
        logger.info(f"Successfully deleted file: {filename}")
        
        return {
            "success": True,
            "message": f"File {filename} deleted successfully",
            "filename": filename,
            "index_updated": True
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

@app.post("/api/rebuild")
async def rebuild_knowledge_base():
    """Rebuild the knowledge base index from scratch"""
    try:
        logger.info("Starting knowledge base rebuild...")
        
        # Call the rebuild function from RAG module
        result = rebuild_index()
        
        if result.get("success"):
            logger.info("Knowledge base rebuilt successfully")
            return {
                "success": True,
                "message": "Knowledge base rebuilt successfully",
                "result": result,
                "timestamp": result.get("timestamp")
            }
        else:
            logger.error(f"Knowledge base rebuild failed: {result.get('error')}")
            raise HTTPException(
                status_code=500, 
                detail=f"Knowledge base rebuild failed: {result.get('error')}"
            )
            
    except Exception as e:
        logger.error(f"Failed to rebuild knowledge base: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to rebuild knowledge base: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Health check endpoint to verify system status"""
    try:
        # Check if docs directory exists and is accessible
        docs_accessible = os.access(docs_dir, os.R_OK)
        
        # Check if index directory exists
        index_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/index'))
        index_exists = os.path.exists(index_dir)
        
        # Count files
        file_count = len([f for f in Path(docs_dir).iterdir() if f.is_file()]) if docs_accessible else 0
        
        return {
            "status": "healthy",
            "docs_directory": {
                "path": docs_dir,
                "accessible": docs_accessible,
                "file_count": file_count
            },
            "index_directory": {
                "path": index_dir,
                "exists": index_exists
            },
            "timestamp": os.path.getmtime(index_dir) if index_exists else None
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }