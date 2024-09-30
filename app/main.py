import os
from pathlib import Path
import random
import shutil
from fastapi import FastAPI, Depends, File, Header, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

import models
import schemas
from database import engine, async_get_db

app = FastAPI(title="Twitter Clone")
app_api = FastAPI()

app.mount("/api", app_api)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

NAMES = ['Tom', 'Anna', 'Jason', 'Samantha', 'Erik', 'George', 'Julia', 'Emma']

OUT_PATH = Path(__file__).parent / 'images'


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)


@app.on_event("shutdown")
async def shutdown(session: AsyncSession = Depends(async_get_db)):
    await session.close()
    await engine.dispose()


@app.get("/", response_class=HTMLResponse)
async def get_root() -> HTMLResponse:
    """Отображение фронтенда"""
    return HTMLResponse("index.html")


@app_api.get("/app/images/{file_name}")
async def get_image_from_dir(file_name: str):
    """Эндпойнт для загрузки сохраненных картинок в ленту с твитами"""
    file_path = f"images/{file_name}"
    return FileResponse(file_path)


@app_api.get("/users/me")
async def get_current_user_info(session: AsyncSession = Depends(async_get_db),
                                api_key: str = Header(None)):
    """Эндпойнт получения информации о своём профиле + создание нового пользователя"""

    if not api_key:
        response = jsonable_encoder({"message": "Please, provide http-header 'Api-key' in your request"})
        return JSONResponse(content=response, status_code=400)
    else:
        res = await session.execute(select(models.User).where(
            models.User.api_key == api_key).options(
            selectinload(models.User.following),
                    selectinload(models.User.subscribers))
        )
        user = res.scalar()

        if not user:
            user = models.User(name=random.choice(NAMES), api_key=api_key)
            session.add(user)
            await session.commit()

            return {
                "result": True,
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "followers": [],
                    "following": [],
                },
            }

        followers = [{"id": follower.id, "name": follower.name} for follower in user.subscribers]
        following = [{"id": following.id, "name": following.name} for following in user.following]

        return {
            "result": True,
            "user": {
                "id": user.id,
                "name": user.name,
                "followers": followers,
                "following": following,
            },
        }


@app_api.post("/tweets/{tweet_id}/likes")
async def like_tweet(tweet_id: int,
                     session: AsyncSession = Depends(async_get_db),
                     api_key: str = Header(None)):
    """Эндпойнт, который позволяет пользователю поставить отметку «Нравится» на твит"""

    res_user = await session.execute(select(models.User).filter(models.User.api_key == api_key))
    user = res_user.scalar()

    res_tweet = await session.execute(select(models.Tweet).filter(models.Tweet.id == tweet_id))
    tweet = res_tweet.scalar()

    like = models.Like(user_id=user.id, tweet_id=tweet.id)
    session.add(like)
    await session.commit()

    response = {"result": True}
    return JSONResponse(content=jsonable_encoder(response), status_code=201)


@app_api.delete("/tweets/{tweet_id}/likes")
async def delete_like_from_tweet(tweet_id: int,
                                 session: AsyncSession = Depends(async_get_db),
                                 api_key: str = Header(None)):
    """Эндпойнт, который позволяет пользователю убрать отметку «Нравится» с твита"""

    res_user = await session.execute(select(models.User).filter(models.User.api_key == api_key))
    user = res_user.scalar()

    res_like = await session.execute(select(models.Like).filter(
        models.Like.tweet_id == tweet_id, models.Like.user_id == user.id
    ))
    like = res_like.scalar()

    await session.delete(like)
    await session.commit()

    return {"result": True}


@app_api.post("/users/{user_id}/follow")
async def follow_user(user_id: int,
                     session: AsyncSession = Depends(async_get_db),
                     api_key: str = Header(None)):
    """Эндпойнт, который позволяет пользователю зафоловить другого пользователя"""

    res_curr_user = await session.execute(select(models.User).filter(
        models.User.api_key == api_key).options(
            selectinload(models.User.following),
                    selectinload(models.User.subscribers)
        )
    )
    current_user = res_curr_user.scalar()

    res_follow_user = await session.execute(select(models.User).filter(
        models.User.id == user_id).options(
            selectinload(models.User.following),
                    selectinload(models.User.subscribers)
        )
    )
    following_user = res_follow_user.scalar()

    current_user.following.append(following_user)
    await session.commit()

    response = {"result": True}
    return JSONResponse(content=jsonable_encoder(response), status_code=201)


@app_api.delete("/users/{user_id}/follow")
async def unsubscribe_from_user(user_id: int,
                     session: AsyncSession = Depends(async_get_db),
                     api_key: str = Header(None)):
    """Эндпойнт, который позволяет пользователю убрать подписку на другого пользователя"""

    res_curr_user = await session.execute(select(models.User).filter(
        models.User.api_key == api_key).options(
            selectinload(models.User.following),
                    selectinload(models.User.subscribers)
        )
    )
    current_user = res_curr_user.scalar()

    res_follow_user = await session.execute(select(models.User).filter(
        models.User.id == user_id).options(
            selectinload(models.User.following),
                    selectinload(models.User.subscribers)
        )
    )
    following_user = res_follow_user.scalar()

    current_user.following.remove(following_user)
    await session.commit()

    return {"result": True}


@app_api.delete("/tweets/{tweet_id}")
async def delete_tweet_by_id(tweet_id: int, session: AsyncSession = Depends(async_get_db), api_key: str = Header(None)):
    """Эндпойнт для удаления пользователем своего твита по id"""

    res_user = await session.execute(select(models.User).filter(models.User.api_key == api_key))
    user = res_user.scalar()

    res_tweet = await session.execute(select(models.Tweet).filter(
        models.Tweet.id == tweet_id, models.Tweet.user_id == user.id
    ))
    tweet = res_tweet.scalar()

    if not tweet:
        response = {
            "result": False,
            "error_type": "PermissionError",
            "error_message": "User does not have permission to delete the tweet"
        }
        return JSONResponse(content=jsonable_encoder(response), status_code=400)

    await session.delete(tweet)
    await session.commit()

    return {"result": True}


@app_api.get("/users/{user_id}")
async def get_user_info_by_id(user_id: int, session: AsyncSession = Depends(async_get_db)):
    """Эндпойнт получения информации о произвольном профиле по его id"""

    res = await session.execute(select(models.User).where(
        models.User.id == user_id).options(
        selectinload(models.User.following),
        selectinload(models.User.subscribers))
    )
    user = res.scalar()
    if not user:
        response = {
            "result": False,
            "error_type": "NotFound",
            "error_message": "User not found"
        }
        return JSONResponse(content=jsonable_encoder(response), status_code=404)

    followers = [{"id": follower.id, "name": follower.name} for follower in user.subscribers]
    following = [{"id": following.id, "name": following.name} for following in user.following]
    return {
        "result": True,
        "user": {
            "id": user.id,
            "name": user.name,
            "followers": followers,
            "following": following,
        },
    }


@app_api.get("/tweets")
async def get_tweets_list(session: AsyncSession = Depends(async_get_db),
                          api_key: str = Header(None)):
    """Эндпойнт получения ленты с твитами"""

    res_tweets = await session.execute(select(models.Tweet))
    tweets = res_tweets.scalars().all()
    tweets_data = []

    for tweet in tweets:
        attachments = [image.url for image in tweet.image]
        likes = [{"user_id": like.user.id, "name": like.user.name} for like in tweet.likes]
        tweet_info = {
            "id": tweet.id,
            "content": tweet.content,
            "attachments": attachments,
            "author": {"id": tweet.author.id, "name": tweet.author.name},
            "likes": likes,
        }
        tweets_data.append(tweet_info)
    return {"result": True, "tweets": tweets_data}


@app_api.post("/tweets")
async def post_tweet(tweet: schemas.TweetIn,
                     session: AsyncSession = Depends(async_get_db),
                     api_key: str = Header(None)):
    """Эндпойнт добавления нового твита"""

    res_user = await session.execute(select(models.User).filter(models.User.api_key == api_key))
    user = res_user.scalar()
    new_tweet = models.Tweet(content=tweet.tweet_data, user_id=user.id)
    session.add(new_tweet)
    await session.commit()

    if tweet.tweet_media_ids:
        res = await session.execute(select(models.Image).filter(
            models.Image.id.in_(tweet.tweet_media_ids)
        ))
        images = res.scalars().all()
        for image in images:
            image.tweet_id = new_tweet.id
        await session.commit()

    response = {"result": True, "tweet_id": new_tweet.id}
    return JSONResponse(content=jsonable_encoder(response), status_code=201)


@app_api.post("/medias")
async def download_image_from_tweet(file: UploadFile = File(...),
                                    session: AsyncSession = Depends(async_get_db),
                                    api_key: str = Header(None)):
    """Эндпойнт для загрузки картинок из твита"""

    os.makedirs(OUT_PATH, exist_ok=True)

    file_path = "{}/{}".format(OUT_PATH, file.filename)
    with open(file_path, mode='wb') as f:
        shutil.copyfileobj(file.file, f)


    new_image = models.Image(url=f"api{file_path}")
    session.add(new_image)
    await session.commit()

    response = {"result": True, "media_id": new_image.id}
    return JSONResponse(content=jsonable_encoder(response), status_code=201)
