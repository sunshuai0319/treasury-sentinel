from app.integrations.keeperhub import KeeperHubClient


def test_keeperhub_execution_maps_camel_and_snake_case_fields():
    execution = KeeperHubClient._execution_from_json(
        {
            "id": "exec_1",
            "status": "confirmed",
            "transactionHash": "0xabc",
            "errorCode": None,
        }
    )

    assert execution.execution_id == "exec_1"
    assert execution.status == "confirmed"
    assert execution.transaction_hash == "0xabc"
