from io import BytesIO

DATA = {"tweet_data": "Hello, World!", "tweet_media_ids": []}


async def test_status_200(async_client):
    response = await async_client.get("/users/me")

    assert response.status_code == 200
    assert response.json()["user"]["id"] == 1
    assert response.json()["user"]["name"] == "Anton"


async def test_create_tweet(async_client):
    response = await async_client.post("/tweets", json=DATA)

    assert response.status_code == 201
    assert response.json() == {"result": True, "tweet_id": 1}


async def test_media_route(async_client):
    image_content = b"Hello, World!"
    image_file = BytesIO(image_content)
    files = {"file": ("test.txt", image_file)}
    response = await async_client.post("/medias", files=files)

    assert response.status_code == 201
    assert response.json() == {"result": True, "media_id": 1}


async def test_delete_tweet(async_client):
    response = await async_client.post("/tweets", json=DATA)
    response_delete = await async_client.delete("/tweets/1")
    response_tweets = await async_client.get("/tweets")

    assert response.json() == {"result": True, "tweet_id": 1}
    assert response_delete.status_code == 200
    assert len(response_tweets.json()["tweets"]) == 0


async def test_delete_wrong_tweet(async_client):
    response = await async_client.post("/tweets", json=DATA, headers={"api-key": "test_key"})
    response_delete = await async_client.delete("/tweets/1")
    response_tweets = await async_client.get("/tweets")

    assert response.json() == {"result": True, "tweet_id": 1}
    assert response_delete.status_code == 400
    assert "User does not have permission to delete" in response_delete.text
    assert len(response_tweets.json()["tweets"]) == 1


async def test_add_like_to_tweet(async_client):
    response_tweet = await async_client.post("/tweets", json=DATA)
    response_like = await async_client.post("/tweets/1/likes")
    response = await async_client.get("/tweets")

    assert response_tweet.status_code == 201
    assert response_like.status_code == 201
    assert response_like.json() == {"result": True}
    assert len(response.json()["tweets"][0]["likes"]) == 1


async def test_delete_like_from_tweet(async_client):
    response_tweet = await async_client.post("/tweets", json=DATA)
    response_like = await async_client.post("/tweets/1/likes")
    response_like_delete = await async_client.delete("/tweets/1/likes")
    response = await async_client.get("/tweets")

    assert response_tweet.status_code == 201
    assert response_like.status_code == 201
    assert response_like_delete.status_code == 200
    assert response_like_delete.json() == {"result": True}
    assert len(response.json()["tweets"][0]["likes"]) == 0


async def test_follow_user(async_client):
    response = await async_client.post("/users/2/follow")
    response_me = await async_client.get("/users/me")
    response_user = await async_client.get("/users/2")

    assert response.status_code == 201
    assert response.json() == {"result": True}
    assert len(response_me.json()["user"]["following"]) == 1
    assert len(response_user.json()["user"]["followers"]) == 1


async def test_unfollow_user(async_client):
    response_follow = await async_client.post("/users/2/follow")
    response = await async_client.delete("/users/2/follow")
    response_me = await async_client.get("/users/me")
    response_user = await async_client.get("/users/2")

    assert response_follow.status_code == 201
    assert response.status_code == 200
    assert response.json() == {"result": True}
    assert len(response_me.json()["user"]["following"]) == 0
    assert len(response_user.json()["user"]["followers"]) == 0


async def test_get_tweets(async_client):
    response_tweet = await async_client.post("/tweets", json=DATA)
    response = await async_client.get("/tweets")

    assert response_tweet.status_code == 201
    assert response.status_code == 200
    assert len(response.json()["tweets"]) == 1
    assert response.json()["tweets"][0]["content"] == "Hello, World!"
    assert response.json()["tweets"][0]["author"]["name"] == "Anton"


async def test_get_user_by_id(async_client):
    response = await async_client.get("/users/2")
    assert response.status_code == 200
    assert response.json()["user"]["id"] == 2
    assert response.json()["user"]["name"] == "Ivan"
