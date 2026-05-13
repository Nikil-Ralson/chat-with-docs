from dotenv import load_dotenv
load_dotenv()

from os import getenv
import streamlit as st
from db import Tags

st.set_page_config(page_title="Manage Tags")
st.title("Manage Tags")

# Create tag
st.subheader("Create a Tag")
tag_name = st.text_input("Tag name", placeholder="e.g. Finance, Legal, HR …")

if st.button("Create Tag", type="primary"):
    if tag_name.strip():
        if Tags.select().where(Tags.name == tag_name.strip()).exists():
            st.warning(f"Tag '{tag_name}' already exists.")

        else:
            Tags.create(name=tag_name.strip())
            st.success(f"Tag '{tag_name}' created!")
            st.rerun()
    else:
        st.error("Please enter a tag name.")

st.divider()

st.subheader("Existing Tags")
tags = list(Tags.select().order_by(Tags.name))

if not tags:
    st.info("No tags yet. Create one above!")
else:
    for tag in tags:
        col1, col2 = st.columns([5, 1])
        col1.write(f" {tag.name}")
        if col2.button("Delete", key=f"del_tag_{tag.id}"):
            tag.delete_instance(recursive=True)
            st.success(f"Deleted tag '{tag.name}'")
            st.rerun()
