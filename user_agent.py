import asyncio

from src.agents.user_agent import UserAgentDependencies, user_agent
from src.database.db import db_manager, get_db_session
from src.services.user_service import UserService


async def main():
    db_manager.drop_db()
    db_manager.init_db()

    with get_db_session() as db:
        us = UserService(db)
        test_user = us.create_user(name="test", email="dwell@gmail.com")
        deps = UserAgentDependencies(db=db, user=test_user)

        await user_agent.to_cli(deps=deps, prog_name="dwell")


if __name__ == "__main__":
    asyncio.run(main())
