from os import getenv
import streamlit as st

st.set_page_config(
    page_title="Chat With Docs",
    layout="wide",
)

st.title("📄 Chat With Docs")
st.markdown(
    """
    Welcome! Use the sidebar to navigate between pages:
    - **Manage Tags** — create and delete tags
    - **Manage Documents** — upload PDFs and assign tags
    - **Chat With Documents** — ask questions about your documents
    
    > 🆓 Powered entirely by **free local models** — no OpenAI key required!
    """
)

st.info(
    "**Stack:** sentence-transformers for embeddings · Ollama (or Groq free tier) for LLM · "
    "PostgreSQL + pgvector for vector search"
)

