# Two FastAPI services
find more in the directories

## Installation
1. `git clone https://github.com/alexfomin1/webtronics.git`
2. Use instructions inside the services' directories

## Endpoint
API to return encoded link

## Social network
Simple social network service (on FastAPI)
Runs with `docker-compose`
Uses following elements:
- FastAPI (python-3.10.9)
- Redis
- SQLite

## Structure
.
├── README.md
├── endpoint
│   ├── README.md
│   ├── app
│   │   └── main.py
│   ├── poetry.lock
│   ├── pyproject.toml
│   └── requirements.txt
└── social_network
    ├── Dockerfile
    ├── README.md
    ├── app
    │   ├── __init__.py
    │   ├── config.py
    │   ├── db.sqlite3
    │   ├── main.py
    │   └── test.py
    ├── docker-compose.yml
    ├── poetry.lock
    ├── pyproject.toml
