# Social network API

## Features
- Sign Up & Sign In
- Email validation while signing up with `hunter.io`/`emailhunter.co`
- Create, edit, view & delete posts
- Like & dislike posts (but not your own)
- Likes & dislikes are stored in Redis
- Run the service with `docker-compose`
- JWT&Oauth2 authentication
- API documentation at `/docs`
- SQLite database
- Mostly async

## Elements
- FastAPI
- aiohttp
- redis.asyncio
- SQLite db
- Tortoise-ORM

## Installation
0. Install & run Docker
1. `docker-compose up -d --build` to start the service
2. Find the service at `localhost:8000`, Swagger UI docs will help you at `localhost:8000/docs`
3. `docker-compose stop` to stop it

## Structure
.
├── Dockerfile
├── README.md
├── app
│   ├── __init__.py
│   ├── config.py
│   ├── db.sqlite3
│   └── main.py
├── docker-compose.yml
├── poetry.lock
├── pyproject.toml

