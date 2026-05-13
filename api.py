from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import fitz
from db import Documents, Tags, DocumentTags, DocumentInformationChunks, db
from llms import get_embedding, chat, chat_json
from constants import CREATE_FACT_CHUNKS_SYSTEM_PROMPT, RESPOND_TO_MESSAGE_SYSTEM_PROMPT
from utils import find

app = FastAPI(title="chat with docs API")

@app.on_event("startup")
async def startup_event():
    try:
        get_embedding("warmup")
        print("Embedding model loaded successfully!")
    except Exception as e:
        print(f"Warning: Could not preload embedding model: {e}")

@app.get("/")
def root():
    return {"status": "ok", "message": "Welcome to the chat with docs API!"}

#upload document
@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code = 400, detail="Only PDF files are supported")
    
    contents = await file.read()
    pdf = fitz.open(stream=contents, filetype="pdf")
    full_text = "\n\n".join(page.get_text() for page in pdf)

    if not full_text.strip():
        raise HTTPException(status_code = 400, detail="Could not extract text from PDF.")
    
    document = Documents.create(name=file.filename)

    try:
        result = chat_json(CREATE_FACT_CHUNKS_SYSTEM_PROMPT, full_text[:8000])
        facts = result.get("facts", [])
    except Exception:
        facts = [p.strip() for p in full_text.split("\n\n") if p.strip()]

    for fact in facts:
        embedding = get_embedding(fact)
        DocumentInformationChunks.create(
            document_id = document.id,
            chunk=fact,
            embedding=embedding
        )
    return {
        "message": "Document uploaded successfully",
        "document_id": document.id,
        "document_name": file.filename,
        "chunks_created": len(facts)
    }

#list documentse
@app.get("/documents")
def list_documents():
    documnents = list(Documents.select().order_by(Documents.name))
    return {
        "documents": [
            {
                "id": doc.id,
                "name": doc.name,
                "chunks": DocumentInformationChunks.select()
                .where(DocumentInformationChunks.document_id == doc.id)
                .count()
            }
            for doc in documnents
        ]
    }

#Delete document
@app.delete("/documents/{document_id}")
def delte_document(document_id):
    try:
        doc = Documents.get_by_id(document_id)
        doc.delete_instance(recursive=True)
        return { "message": f"Document {document_id} deleted successfully"}
    except Documents.DoesNotExist:
        raise HTTPException(status_code=404, detail="Document not found")
    
#Chat
class ChatRequest(BaseModel):
    question: str
    top_k: int=5

@app.post("/chat")
def chat_with_docs(request: ChatRequest):
    query_embedding = get_embedding(request.question)

    chunks = (
        DocumentInformationChunks
        .select(
            DocumentInformationChunks,
            DocumentInformationChunks.embedding.cosine_distance(query_embedding).alias("distance")
        )
        .order_by(db.execute_sql("distance"))
        .limit(request.top_k)
    )
    chunks = list(chunks)

    if not chunks:
        return {"answer": "No relevant information found in documents.", " sources": []}
    
    knowledge = "\n".join(f"- {c.chunk} for c in chunks")
    system_prompt = RESPOND_TO_MESSAGE_SYSTEM_PROMPT.replace("{{knowledge}}", knowledge)
    answer = chat(system_prompt, request.question)

    sources = []
    for c in chunks:
        doc = Documents.get_by_id(c.document_id)
        sources.append({"document": doc.name, "chunk": c.chunk})
    return {"answer": answer, "sources": sources}

#Tags
@app.get("/tags")
def list_tags():
    tags = list(Tags.select().order_by(Tags.name))
    return {"tags": [{"id": t.id, "name": t.name} for t in tags]}


@app.post("/tags")
def create_tag(name: str):
    if Tags.select().where(Tags.name == name).exists():
        raise HTTPException(status_code=400, detail="Tag already exists")
    tag = Tags.create(name=name)
    return {"id": tag.id, "name": tag.name}

@app.middleware("http")
async def db_connection_middleware(request, call_next):
    if db.is_closed():
        db.connect()
    try:
        response = await call_next(request)
    finally:
        if not db.is_closed():
            db.close()
    return response