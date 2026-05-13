from dotenv import load_dotenv
load_dotenv()

from os import getenv
import json
import streamlit as st
import fitz
from db import Documents, Tags, DocumentTags, DocumentInformationChunks
from llms import get_embedding, chat_json
from constants import CREATE_FACT_CHUNKS_SYSTEM_PROMPT, GET_MATCHING_TAGS_SYSTEM_PROMPT
from utils import find

st.set_page_config(page_title="Manage Documents")
st.title("Manage Documents")

st.subheader("Upload a PDF Document")

uploaded_file = st.file_uploader("Choose a PDF", type=["pdf"])

if uploaded_file is not None:
    doc_name = st.text_input("Document name", value=uploaded_file.name)

    #Tag selection
    all_tags = list(Tags.select().order_by(Tags.name))
    tag_options = {t.name: t for t in all_tags}
    selected_tag_names = st.multiselect(
        "Assign tags (or leave empty forauto-tagging)",
        options=list(tag_options.keys())
    )
    auto_tag = st.checkbox("Auto-detect additional tags using AI", value=True)

    if st.button("Upload & Process", type="primary"):
        if not doc_name.strip():
            st.error("Please provide a document name.")
        else:
            with st.status("Processing document…", expanded=True) as status:
                st.write("Extracting text from pdf...")
                pdf = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                full_text = "\n\n".join(page.get_text() for page in pdf)

                if not full_text.strip():
                    st.stop()

                st.write("Saving document record")
                document = Documents.create(name=doc_name.strip())

                st.write("Extracting facts from text.")
                try:
                    result = chat_json(CREATE_FACT_CHUNKS_SYSTEM_PROMPT, full_text[:8000])
                    facts = result.get("facts", [])
                except Exception as e:
                    st.warning(f"Fact extraction failed ({e}), falling back to paragraph chunking.")
                    facts = [p.strip() for p in full_text.split("\n\n") if p.strip()]

                st.write(f"Extracted {len(facts)} facts/chunks")

                st.write("Generating embeddings locally .")
                progress = st.progress(0)
                for i, fact in enumerate(facts):
                    embedding = get_embedding(fact)
                    DocumentInformationChunks.create(document_id=document.id, chunk=fact, embedding=embedding)
                    progress.progress((i + 1) / len(facts))

                st.write("Assigning tags")
                assigned_tags = [tag_options[n] for n in selected_tag_names if n in tag_options]

                if auto_tag and all_tags:
                    tag_names_list = [t.name for t in all_tags]
                    prompt = GET_MATCHING_TAGS_SYSTEM_PROMPT.replace("{{tags_to_match_with}}", json.dumps(tag_names_list))
                    try:
                        tag_result = chat_json(prompt, full_text[:4000])
                        suggested_names = tag_result.get("tags", [])
                        for  name in suggested_names:
                            tag = find(lambda t, n=name: t.name == n , all_tags)
                            if tag and tag not in assigned_tags:
                                assigned_tags.append(tag)
                    except Exception as e:
                        st.warning(f"Auto-tagging failed: {e}")

                for tag in assigned_tags:
                    DocumentTags.create(document_id=document, tag_id=tag)

            st.success(
                f"Uploaded **{doc_name}** with {len(facts)} chunks and "
                f"{len(assigned_tags)} tag(s): {', '.join(t.name for t in assigned_tags) or 'none'}"
            )

st.divider()

# Existing documents
st.subheader("Existing Documents")
documents = list(Documents.select().order_by(Documents.name))

if not documents:
    st.info("No documents uploaded yet.")

else:
    for doc in documents:
        tags = [dt.tag_id for dt in DocumentTags.select().where(DocumentTags.document_id == doc)]
        chunk_count = DocumentInformationChunks.select().where(DocumentInformationChunks.document_id == doc).count()

        with st.expander(f" {doc.name}  ({chunk_count} chunks)"):
            if tags:
                st.write("Tags: " + ", ".join(f" {t.name}" for t in tags))
            else:
                st.write("Tags: none")

            if st.button("Delete Document", key=f"del_doc_{doc.id}"):
                doc.delete_instance(recursive=True)
                st.success(f"Deleted '{doc.name}'")
                st.rerun() 
