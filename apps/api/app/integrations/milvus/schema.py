from pymilvus import CollectionSchema, DataType, FieldSchema


def policy_collection_schema(dimension: int) -> CollectionSchema:
    fields = [
        FieldSchema("chunk_id", DataType.VARCHAR, is_primary=True, max_length=128),
        FieldSchema("document_id", DataType.VARCHAR, max_length=128),
        FieldSchema("policy_version", DataType.INT64),
        FieldSchema("section_id", DataType.VARCHAR, max_length=64),
        FieldSchema("title", DataType.VARCHAR, max_length=512),
        FieldSchema("content", DataType.VARCHAR, max_length=4096),
        FieldSchema("document_type", DataType.VARCHAR, max_length=64),
        FieldSchema("payment_category", DataType.VARCHAR, max_length=64),
        FieldSchema("approval_level", DataType.VARCHAR, max_length=64),
        FieldSchema("effective_from", DataType.INT64),
        FieldSchema("effective_to", DataType.INT64),
        FieldSchema("content_hash", DataType.VARCHAR, max_length=64),
        FieldSchema("embedding", DataType.FLOAT_VECTOR, dim=dimension),
    ]
    return CollectionSchema(fields, enable_dynamic_field=False)


POLICY_INDEX_PARAMS = {
    "index_type": "AUTOINDEX",
    "metric_type": "COSINE",
    "params": {},
}

