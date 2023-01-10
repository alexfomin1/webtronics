from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from tortoise import fields
from tortoise.models import Model
from tortoise.contrib.fastapi import register_tortoise
from tortoise.contrib.pydantic import pydantic_model_creator
from passlib.hash import bcrypt
from jose import jwt
from pydantic import BaseModel, validator, ValidationError, EmailStr
import aiohttp
import redis.asyncio as redis

from .config import (
    db_url,
    JWT_SECRET,
    hunter_io_key,
    redis_url_likes,
    redis_url_dislikes,
)

description = """
service for webtronics
"""

app = FastAPI(
    title="Social Network API",
    description=description,
    version="0.0.1",
    contact={
        "name": "Aleksey Fomin",
        "url": "https://github.com/alexfomin1",
        "email": "me@fomin3.ru",
    },
)


class User(Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(128, unique=True)
    email = fields.CharField(128)
    password_hash = fields.CharField(220)

    def verify_password(self, password):
        return bcrypt.verify(password, self.password_hash)


class Post(Model):
    id = fields.IntField(pk=True)
    text = fields.TextField()
    amount_of_likes = fields.IntField(default=0)
    amount_of_dislikes = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    modified_at = fields.DatetimeField(auto_now=True)

    author: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User",
        related_name="posts",
    )


User_Pydantic = pydantic_model_creator(User, name="User")
UserIn_Pydantic = pydantic_model_creator(User, name="UserIn", exclude_readonly=True)
Post_Pydantic = pydantic_model_creator(Post, name="Post")
PostIn_Pydantic = pydantic_model_creator(
    Post,
    name="PostIn",
    exclude=("amount_of_likes", "amount_of_dislikes"),
    exclude_readonly=True,
)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def authenticate_user(username: str, password: str):
    user = await User.get(username=username)
    if not user:
        return False
    if not user.verify_password(password):
        return False
    return user


async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user = await User.get(id=payload.get("id"))
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    return await User_Pydantic.from_tortoise_orm(user)


async def check_your_post(post_id, user_id):
    post = await Post.get(id=post_id)

    if post.author_id == user_id:
        return True
    else:
        return False


@app.post("/token")
async def generate_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(
        username=form_data.username, password=form_data.password
    )

    if not user:
        return {"error": "invalid credentials"}

    user_obj = await User_Pydantic.from_tortoise_orm(user)

    token = jwt.encode(user_obj.dict(), JWT_SECRET)

    return {"access_token": token, "token_type": "bearer"}


@app.post("/signup", response_model=User_Pydantic)
async def sign_up(user: UserIn_Pydantic):
    try:
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False)
        ) as session:
            async with session.get(
                f"https://api.hunter.io/v2/email-verifier?email={user.email}&api_key={hunter_io_key}"
            ) as response:
                data = await response.json()

                if (
                    data["data"]["result"] != "deliverable"
                    and data["data"]["status"] != "webmail"
                ):
                    raise Exception

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="Invalid email (validation via hunter.io)",
        )
    user_obj = User(
        username=user.username,
        email=user.email,
        password_hash=bcrypt.hash(user.password_hash),
    )
    await user_obj.save()
    return await User_Pydantic.from_tortoise_orm(user_obj)


@app.post("/signin")
async def sign_in(current_user: UserIn_Pydantic = Depends(get_current_user)):
    return await User_Pydantic.from_tortoise_orm(current_user)


@app.get("/posts", response_model=list[Post_Pydantic])
async def get_posts(current_user: UserIn_Pydantic = Depends(get_current_user)):
    return await Post_Pydantic.from_queryset(Post.all())


@app.post("/create_post", response_model=Post_Pydantic)
async def create_post(
    post: PostIn_Pydantic, current_user: UserIn_Pydantic = Depends(get_current_user)
):
    post_obj = Post(text=post.text, author_id=current_user.id)
    await post_obj.save()
    return await Post_Pydantic.from_tortoise_orm(post_obj)


@app.delete("/delete_post/{post_id}")
async def delete_post(
    post_id: int, current_user: UserIn_Pydantic = Depends(get_current_user)
):
    if not await check_your_post(post_id=post_id, user_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="It is not your post"
        )
    deleted_post = await Post.filter(id=post_id).delete()

    if not deleted_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Post {post_id} not found"
        )
    try:
        r_likes = await redis.from_url(redis_url_likes, decode_responses=True)
        await r_likes.delete(post_id)
        await r_likes.close()
    except Exception:
        pass
    try:
        r_dislikes = await redis.from_url(redis_url_likes, decode_responses=True)

        await r_dislikes.delete(post_id)

        await r_dislikes.close()
    except Exception:
        pass
    return {"deleted_post": post_id}


@app.put("/edit_post/{post_id}")
async def edit_post(
    post_id: int,
    text_new: str,
    current_user: UserIn_Pydantic = Depends(get_current_user),
):
    if not await check_your_post(post_id=post_id, user_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="It is not your post"
        )

    edited_post = await Post.filter(id=post_id).update(text=text_new)

    if not edited_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Post {post_id} not found"
        )
    updated_post = await Post.get(id=post_id)

    return {"edited_post": await Post_Pydantic.from_tortoise_orm(updated_post)}


@app.post("/like_post/{post_id}")
async def like_post(
    post_id: int, current_user: UserIn_Pydantic = Depends(get_current_user)
):
    if await check_your_post(post_id=post_id, user_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You cannot like your posts",
        )
    edited_post = await Post.filter(id=post_id)

    if not edited_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Post {post_id} not found"
        )

    r = await redis.from_url(redis_url_likes, decode_responses=True)
    edited_post = await Post.get(id=post_id)
    if edited_post.amount_of_likes > 0:
        await r.set(post_id, edited_post.amount_of_likes)
    await r.incr(post_id, amount=1)
    amount_of_likes = await r.get(post_id)
    await r.close()

    await Post.filter(id=post_id).update(amount_of_likes=amount_of_likes)

    return {"post_id": post_id, "amount_of_likes": amount_of_likes}


@app.post("/dislike_post/{post_id}")
async def dislike_post(
    post_id: int, current_user: UserIn_Pydantic = Depends(get_current_user)
):
    if await check_your_post(post_id=post_id, user_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You cannot dislike your posts",
        )
    edited_post = await Post.filter(id=post_id)

    if not edited_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Post {post_id} not found"
        )
    r = await redis.from_url(redis_url_dislikes, decode_responses=True)
    edited_post = await Post.get(id=post_id)
    if edited_post.amount_of_dislikes > 0:
        await r.set(post_id, edited_post.amount_of_dislikes)
    await r.incr(post_id, amount=1)
    amount_of_dislikes = await r.get(post_id)
    await r.close()

    await Post.filter(id=post_id).update(amount_of_dislikes=amount_of_dislikes)

    return {"post_id": post_id, "amount_of_dislikes": int(amount_of_dislikes)}


register_tortoise(
    app,
    db_url=db_url,
    modules={"models": ["app.main"]},
    generate_schemas=True,
    add_exception_handlers=True,
)
