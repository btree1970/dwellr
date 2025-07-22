import json
from typing import List, Optional

from pydantic import BaseModel, Field


class SearchTool(BaseModel):
    query: str = Field(description="The search query to execute")
    limit: Optional[int] = Field(default=10, description="Maximum number of results")
    filters: Optional[List[str]] = Field(
        default=None, description="Search filters to apply"
    )


def main():
    print(json.dumps(SearchTool.model_json_schema(), indent=2))


if __name__ == "__main__":
    main()
