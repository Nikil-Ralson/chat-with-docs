from dotenv import load_dotenv
load_dotenv()

from os import getenv
from pgvector.peewee import VectorField
from peewee import PostgresqlDatabase, Model, TextField, ForeignKeyField

db = PostgresqlDatabase(
    getenv("POSTGRES_DB_NAME"),
    host=getenv("POSTGRES_DB_HOST"),
    port=getenv("POSTGRES_DB_PORT"),
    user=getenv("POSTGRES_DB_USER"),
    password=getenv("POSTGRES_DB_PASSWORD"),
    sslmode="require",
)

class Documents(Model):
    name = TextField()
    class Meta:
        database = db
        db_table = "documents"

class Tags(Model):
    name = TextField()
    class Meta:
        database = db
        db_table = "tags"

class DocumentTags(Model):
    document_id = ForeignKeyField(Documents, backref="document_tags", on_delete="CASCADE")
    tag_id = ForeignKeyField(Tags, backref="documents_tags", on_delete="CASCADE")
    class Meta:
        database = db
        db_table = "document_tags"

class DocumentInformationChunks(Model):
    document_id = ForeignKeyField(Documents, backref="document_information_chunks", on_delete="CASCADE")
    chunk = TextField()
    embedding = VectorField(dimensions=384)
    class Meta:
        database = db
        db_table = "document_information_chunks"

#DocumentInformationChunks.add_index("embedding vector_cosine_ops", using="diskann")

db.connect()

db.execute_sql("CREATE EXTENSION IF NOT EXISTS vector")

db.create_tables([Documents, Tags, DocumentTags, DocumentInformationChunks])

try:
    db.execute_sql(
        "CREATE INDEX IF NOT EXISTS document_information_chunks_embedding_index"
        " ON document_information_chunks USING hnsw (embedding vector_cosine_ops)"
    )
except Exception as e:
    print(f"Note: Could not create HNSW index: {e}")
