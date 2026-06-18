from pydantic import BaseModel


class BulkPublishReportsResponse(BaseModel):
    published_count: int
