from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi import APIRouter
from fastapi import Request

app = FastAPI()

#
# # @app.get("/")
# # async def root():
# #     return {"message": "Hello World"}
#
#
# @app.get("/hello/{name}")
# async def say_hello(name: str):
#     return {"message": f"Hello {name}"}
#
# @app.get("/dist")
# async def serve():
#     return {{ "/ dist / index.html"}}

# api_app = FastAPI(title="api app")


@app.post("/set_influencers_to_follow")
async def set_influencers_to_follow(request):
    return {}


app = FastAPI(title="main app")

app.mount("/api", app)
app.mount("/", StaticFiles(directory="dist", html=True), name="dist")
