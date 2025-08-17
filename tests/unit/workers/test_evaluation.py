from unittest.mock import Mock, patch

from src.workers.tasks import MIN_CREDIT_THRESHOLD, handle_evaluate_listings
from tests.fixtures.test_data import create_user_with_credits


class TestEvaluation:
    def test_user_eligibility_filtering(self):
        user_sufficient_credits = create_user_with_credits(
            name="Good User",
            credits=1.00,
            preference_profile="Looking for apartments",
        )

        with (
            patch("src.workers.tasks.get_db_manager") as mock_get_manager,
            patch("src.workers.tasks.app.send_task") as mock_send_task,
        ):
            mock_db = Mock()
            mock_get_manager.return_value.get_session.return_value.__enter__.return_value = (
                mock_db
            )

            eligible_users = [user_sufficient_credits]
            mock_query = Mock()
            mock_query.count.return_value = len(eligible_users)
            mock_query.__iter__ = Mock(return_value=iter(eligible_users))
            mock_db.query.return_value.filter.return_value = mock_query

            mock_send_task.return_value = Mock(id="mocked-task-id")

            mock_task = Mock()
            result = handle_evaluate_listings(mock_task)

            assert result["success"] is True
            assert result["users_found"] == 1
            assert result["tasks_created"] == 1

            filter_call = mock_db.query.return_value.filter.call_args[0]
            assert len(filter_call) == 2

    def test_task_coordination_logic(self):
        users = [
            create_user_with_credits(name=f"User {i}", credits=2.00) for i in range(3)
        ]

        with (
            patch("src.workers.tasks.get_db_manager") as mock_get_manager,
            patch("src.workers.tasks.app.send_task") as mock_send_task,
        ):
            mock_db = Mock()
            mock_get_manager.return_value.get_session.return_value.__enter__.return_value = (
                mock_db
            )

            mock_query = Mock()
            mock_query.count.return_value = len(users)
            mock_query.__iter__ = Mock(return_value=iter(users))
            mock_db.query.return_value.filter.return_value = mock_query

            mock_send_task.return_value = Mock(id="mocked-task-id")

            mock_task = Mock()
            result = handle_evaluate_listings(mock_task)

            assert result["success"] is True
            assert result["users_found"] == 3
            assert result["tasks_created"] == 3

            assert mock_send_task.call_count == 3
            for user in users:
                mock_send_task.assert_any_call(
                    "src.workers.tasks.evaluate_user_listings", args=[user.id]
                )

    def test_task_creation_error_handling(self):
        users = [
            create_user_with_credits(name="User 1", credits=2.00),
            create_user_with_credits(name="User 2", credits=3.00),
            create_user_with_credits(name="User 3", credits=1.50),
        ]

        with (
            patch("src.workers.tasks.get_db_manager") as mock_get_manager,
            patch("src.workers.tasks.app.send_task") as mock_send_task,
        ):
            mock_db = Mock()
            mock_get_manager.return_value.get_session.return_value.__enter__.return_value = (
                mock_db
            )

            mock_query = Mock()
            mock_query.count.return_value = len(users)
            mock_query.__iter__ = Mock(return_value=iter(users))
            mock_db.query.return_value.filter.return_value = mock_query

            call_count = 0

            def side_effect(*args, **kwargs):
                nonlocal call_count
                current_call = call_count
                call_count += 1
                if current_call == 1:
                    raise Exception("Task creation failed")
                else:
                    return Mock(id="success-task-id")

            mock_send_task.side_effect = side_effect

            mock_task = Mock()
            result = handle_evaluate_listings(mock_task)

            assert result["success"] is True
            assert result["users_found"] == 3
            assert result["tasks_created"] == 2
            assert mock_send_task.call_count == 3

    def test_credit_threshold_validation(self):
        assert MIN_CREDIT_THRESHOLD == 0.10
        assert isinstance(MIN_CREDIT_THRESHOLD, float)

        users_at_threshold = [
            create_user_with_credits(
                name="At Threshold",
                credits=0.10,
                preference_profile="Looking",
            ),
            create_user_with_credits(
                name="Above Threshold",
                credits=0.11,
                preference_profile="Looking",
            ),
            create_user_with_credits(
                name="Below Threshold",
                credits=0.09,
                preference_profile="Looking",
            ),
        ]

        with (
            patch("src.workers.tasks.get_db_manager") as mock_get_manager,
            patch("src.workers.tasks.app.send_task") as mock_send_task,
        ):
            mock_db = Mock()
            mock_get_manager.return_value.get_session.return_value.__enter__.return_value = (
                mock_db
            )

            eligible_users = [users_at_threshold[0], users_at_threshold[1]]
            mock_query = Mock()
            mock_query.count.return_value = len(eligible_users)
            mock_query.__iter__ = Mock(return_value=iter(eligible_users))
            mock_db.query.return_value.filter.return_value = mock_query

            mock_send_task.return_value = Mock(id="mocked-task-id")

            mock_task = Mock()
            result = handle_evaluate_listings(mock_task)

            assert result["success"] is True
            assert result["users_found"] == 2
            assert result["tasks_created"] == 2

    def test_empty_user_set_handling(self):
        with patch("src.workers.tasks.get_db_manager") as mock_get_manager:
            mock_db = Mock()
            mock_get_manager.return_value.get_session.return_value.__enter__.return_value = (
                mock_db
            )

            mock_query = Mock()
            mock_query.count.return_value = 0
            mock_db.query.return_value.filter.return_value = mock_query

            mock_task = Mock()
            result = handle_evaluate_listings(mock_task)

            assert result["success"] is True
            assert result["users_found"] == 0
            assert result["tasks_created"] == 0
            assert "No users with sufficient credits found" in result["message"]
