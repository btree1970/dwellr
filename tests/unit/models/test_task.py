from src.models.task import Task


def test_task_model_basic():
    """Test basic task model functionality"""
    task = Task(task_type="evaluate_listings", status="pending")

    assert task.task_type == "evaluate_listings"
    assert task.status == "pending"
