from app.integrations.milvus.schema import policy_collection_schema


def test_policy_schema_uses_512_dimension():
    schema = policy_collection_schema(512)
    embedding = next(field for field in schema.fields if field.name == "embedding")

    assert embedding.params["dim"] == 512
    assert schema.enable_dynamic_field is False

