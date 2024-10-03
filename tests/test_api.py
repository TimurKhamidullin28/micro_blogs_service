from httpx import AsyncClient
from io import BytesIO
import pytest


@pytest.mark.asyncio(scope="session")
async def test_media_route(async_client: AsyncClient):
    image_content = b"Hello, World!"
    image_file = BytesIO(image_content)
    files = {"file": ("test.txt", image_file)}
    response = await async_client.post("/medias", files=files)

    assert response.status_code == 201
    assert response.json() == {"result": True, "media_id": 1}
