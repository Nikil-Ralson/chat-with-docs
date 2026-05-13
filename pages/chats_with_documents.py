from dotenv import load_dotenv
load_dotenv()

from os import getenv
import streamlit as st
from pgvector.peewee import VectorField
from peewee import fn, SQL
from db import Documents, Tags, DocumentTags, DocumentInformationChunks, db
from llms import get_embedding, chat
from constants import RESPOND_TO_MESSAGE_SYSTEM_PROMPT

st.set_page_config(page_title="Chat With Documents")
st.title("Chat With Documents")

with st.sidebar:
    st.header("Filters")

    all_tags = list(Tags.select().order_by(Tags.name))
    tag_options = {t.name: t for t in all_tags}
    selected_tag_names = st.multiselect("Filter by tags (optional)", options=list(tag_options.keys()))

    top_k = st.slider("Number of chunks to retrive", min_value=1, max_value=20, value=5)

    st.divider()
    st.caption("**Model info**")
    st.caption("Embeddings: sentence-transformers (local)")
    st.caption("LLM: Groq (see .env)")

#── Chat history ──────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

#── Chat input ────────────────────────────────────────────────────────────────
user_input = st.chat_input("Ask a question about your documents…")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Searching documents..."):

            query_embedding = get_embedding(user_input)

            #Build the similarity query, use pgvector cosine distance operator <=>
            query = (
                DocumentInformationChunks.select(DocumentInformationChunks, DocumentInformationChunks.embedding.cosine_distance(query_embedding).alias("distance"))
                .order_by(SQL("distance")).limit(top_k)
            )

            #Apply tag filter if selected
            if selected_tag_names:
                selected_tag_ids = [tag_options[n].id for n in selected_tag_names]
                doc_ids_with_tags = (
                    DocumentTags.select(DocumentTags.document_id)
                    .where(DocumentTags.tag_id.in_(selected_tag_ids))
                )
                query = query.where(DocumentInformationChunks.document_id.in_(doc_ids_with_tags))

            chunks = list(query)

        if not chunks:
            answer = "I couldn't find any relevant information in your documents for that question."
        else:
            knowledge = "\n".join(f"- {c.chunk}" for c in chunks)
            system_prompt = RESPOND_TO_MESSAGE_SYSTEM_PROMPT.replace("{{knowledge}}", knowledge)

            with st.spinner("Generating answer..."):
                answer = chat(system_prompt, user_input)

        st.markdown(answer)

        # Show sources in expander
        if chunks:
            with st.expander(f"Sources ({len(chunks)} chunks retrieved)"):
                for i, chunk in enumerate(chunks, 1):
                    doc = Documents.get_by_id(chunk.document_id)
                    st.markdown(f"**[{i}] {doc.name}**")
                    st.caption(chunk.chunk)
                    st.divider()

    st.session_state.messages.append({"role": "assistant", "content": answer})
