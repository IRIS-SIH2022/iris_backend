import os
from fastapi import FastAPI, Body, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, EmailStr, Json
from bson import ObjectId
from typing import Optional, List
import motor.motor_asyncio
from dotenv import load_dotenv
import datetime
import time
from fastapi.middleware.cors import CORSMiddleware
import json
import spacy
from spacy.lang.en.stop_words import STOP_WORDS
from string import punctuation
from heapq import nlargest

# from fastapi_users.models import BaseUser, BaseUserCreate, BaseUserUpdate, BaseUserDB


load_dotenv()
app = FastAPI()
client = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGODB_URL"])
db = client.Gotham

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def time_query(string):
    clap = string.split(" - ")
    blob = []
    for i in clap:
        blob.append(int(i.replace(":", "")))
    return {"$gte": blob[0], "$lte": blob[1]}


def date_query(string):
    clap = string.split(" - ")
    blob = []
    for i in clap:
        trip = i.split("/")
        for i in range(0, len(trip)):
            # HACK: If month is more than may then go to 2021
            # else go to 2022
            # Doing this cause our data in db is from ~2021 May to ~2022 May
            if int(trip[1]) >= 5:
                trip[2] = "2021"
            if int(trip[1]) < 5:
                trip[2] = "2022"

            trip[i] = int(trip[i])
        blob.append(
            int(
                time.mktime(
                    datetime.datetime(trip[2], trip[1], trip[0], 00, 00).timetuple()
                )
            )
        )
    return {"$gte": blob[0], "$lte": blob[1]}


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class CrimeDataModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    case_number: str = Field(...)
    lat: float = Field(...)
    lng: float = Field(...)
    time: int = Field(...)
    date: int = Field(...)
    primary_type: str = Field(...)
    description: str = Field(...)
    act_type: str = Field(...)
    StationID: int = Field(...)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "lat": 28.614,
                "lng": 77.203,
                "case_number": "ASDF",
                "time": 1658130003,
                "date": 1658130003,
                "primary_type": "CRIME",
                "description": "description of crime",
                "act_type": "IPC ---",
                "StationID": 12,
            }
        }


class UpdateCrimeData(BaseModel):
    lat: Optional[float]
    lng: Optional[float]
    time: Optional[int]
    date: Optional[int]
    primary_type: Optional[str]
    description: Optional[str]
    act_type: Optional[str]
    StationID: Optional[int]


@app.get("/")
def hello():
    return "hello world"


@app.post(
    "/marker/post_new",
    response_description="Add new crime marker",
    response_model=CrimeDataModel,
)
async def create_marker(crime: CrimeDataModel = Body(...)):
    crime = jsonable_encoder(crime)
    new_crime = await db["CrimeMarkers"].insert_one(crime)
    created_crime = await db["CrimeMarkers"].find_one({"_id": new_crime.inserted_id})
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_crime)


@app.post(
    "/marker/request",
    response_description="JSON request from the front-end",
    response_model=List[CrimeDataModel],
)
async def extract_data(query: dict):
    # query = jsonable_encoder(query)
    # print(query)
    dqb = {}
    query["StationID"] = int(query["StationID"])
    if query["case_number"] != "":
        dqb["case_number"] = query["case_number"]
        # dqb = jsonable_encoder(dqb)
        response = await db["CrimeMarkers"].find(dqb).to_list(1_00_000)
        return response
    else:
        dqb = {k: v for k, v in query.items() if v != ""}
        if query["StationID"] == -1:
            del dqb["StationID"]
        if query["daterange"] != "":
            dqb["date"] = date_query(query["daterange"])
            del dqb["daterange"]
        if query["timerange"] != "":
            dqb["time"] = time_query(query["timerange"])
            del dqb["timerange"]
        # dqb = jsonable_encoder(dqb)
        print(dqb)
        response = await db["CrimeMarkers"].find(dqb).to_list(1_00_000)

        return response


@app.post(
    "/marker/add",
    response_description="Homomorphic entry into database",
    response_model=CrimeDataModel,
)
async def add_marker(raw: dict):
    raw["desc"] = (
        f"Name of reporter: {raw['first_name']} {raw['last_name']}, Contact No. of reporter: {raw['phone']}, Description: {raw['desc']} "
    )

    marker = {
        "lat": float(raw["lat"]),
        "lng": float(raw["lng"]),
        "time": int("".join(raw["time"].split(":"))),
        "StationID": int(raw["StationID"]),
        "description": raw["desc"],
        "case_number": str(raw["case_number"]),
        "act_type": str(raw["act_type"]),
        "primary_type": str(raw["primary_type"]),
    }
    # marker.description = "test"
    trip = raw["date"].split("/")
    for i in range(0, len(trip)):
        trip[i] = int(trip[i])
    marker["date"] = int(
        time.mktime(datetime.datetime(trip[2], trip[1], trip[0], 00, 00).timetuple())
    )
    print(marker)
    marker = jsonable_encoder(marker)
    # temp = json.loads(marker)

    new_marker = await db["CrimeMarkers"].insert_one(marker)
    created_marker = await db["CrimeMarkers"].find_one({"id_": new_marker.inserted_id})
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_marker)


@app.get(
    "/marker",
    response_description="List all crime markers",
    response_model=List[CrimeDataModel],
)
async def list_crime_markers():
    all_crime = await db["CrimeMarkers"].find().to_list(100000)
    return all_crime


class GeoJSONModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="gid")
    type: str = Field(...)
    sho: str = Field(...)
    StationID: int = Field(...)
    name: str = Field(...)
    district: str = Field(...)
    geometry: dict = Field(...)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "type": "Major crime",
                "district": "North Delhi",
                "StationID": 123,
                "sho": "name of officer",
                "geometry": {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [77.206421, 28.627088],
                                [77.218437, 28.61985],
                                [77.212601, 28.61706],
                                [77.212086, 28.610425],
                                [77.208481, 28.612385],
                                [77.205391, 28.610877],
                                [77.201529, 28.611103],
                                [77.201786, 28.617437],
                                [77.199554, 28.617663],
                                [77.199812, 28.623695],
                                [77.206421, 28.627088],
                            ],
                        ],
                    },
                },
            }
        }


class UpdateGeoJSONData(BaseModel):
    type: Optional[str]
    district: Optional[str]
    name: Optional[str]
    sho: Optional[str]
    StationID: Optional[str]
    geometry: Optional[dict]


@app.post(
    "/area", response_description="Add new area polygon", response_model=GeoJSONModel
)
async def create_area(area: GeoJSONModel = Body(...)):
    area = jsonable_encoder(area)
    new_area = await db["GeoJSON"].insert_one(area)
    created_area = await db["GeoJSON"].find_one({"gid": new_area.inserted_id})
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_area)


@app.get(
    "/area",
    response_description="List all area polygons",
    response_model=List[GeoJSONModel],
)
async def list_areas():
    areas = await db["GeoJSON"].find().to_list(1000)
    return areas


@app.get(
    "/station/{id}",
    response_description="Get a single Station Region",
    response_model=List[GeoJSONModel],
)
async def show_area(id: str):
    id = int(id)
    if id == -1:
        areas = await db["GeoJSON"].find().to_list(1000)
        return areas
    elif (area := await db["GeoJSON"].find_one({"StationID": id})) is not None:
        return [area]

    raise HTTPException(status_code=404, detail=f"Area {id} not found")


class CrowdModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    # case_number: str = Field(...)
    lat: float = Field(...)
    lng: float = Field(...)
    time: int = Field(...)
    date: str = Field(...)
    primary_type: str = Field(...)
    description: str = Field(...)
    act_type: str = Field(...)
    StationID: int = Field(...)
    image: str = Field(...)
    address: str = Field(...)
    name: str = Field(...)
    verified: int = Field(...)
    phno: int = Field(...)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "lat": 72.291,
                "lng": 28.73773737369,
                "address": "India Gate",
                "primary_type": "Murder",
                "act_type": "IPC something",
                "description": "Something bad happened",
                "image": "www.4chan.com/sasank",
                "StationID": 23,
                "time": 1230,
                "date": 1672672627,
                "name": "Aman yadav",
                "phno": 9696969696,
                "verified": 1,
            }
        }


@app.get(
    "/list_crowd",
    response_description="List all crowdsource markers",
    response_model=List[CrowdModel],
)
async def list_crowdsource():
    all_crime = await db["CrowdModel"].find().to_list(100000)
    return all_crime


# Write post request to enter data into CrowdModel
@app.post(
    "/crowd_post",
    response_description="Enter single crowdsource marker",
    response_model=CrowdModel,
)
async def crowd_post(marker: CrowdModel = Body(...)):
    area = jsonable_encoder(marker)
    new_area = await db["CrowdModel"].insert_one(area)
    created_area = await db["CrowdModel"].find_one({"_id": new_area.inserted_id})
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_area)


@app.get(
    "/verify/remove/{_id}",
    response_description="Remove marker from database",
    response_model=str,
)
async def remove_marker(_id: str):
    temp = await db["CrowdModel"].delete_one({"_id": _id})
    print(temp)
    return JSONResponse(status_code=status.HTTP_200_OK, content="Deleted")


@app.post(
    "/verify/accept/",
    response_description="Accept marker from database and add it to CrimeMarker DB",
    response_model=CrimeDataModel,
)
async def accept_marker(clap: dict):
    print(clap)
    raw = await db["CrowdModel"].find_one({"_id": clap["_id"]})
    mass_desc = f"Name of reporter: {raw['name']}, Contact No. of reporter: {raw['phno']}, Address: {raw['address']}, Description: {raw['description']} "
    marker = {
        "lat": float(raw["lat"]),
        "lng": float(raw["lng"]),
        # "time": int("".join(raw["time"].split(":"))),
        "StationID": int(raw["StationID"]),
        "description": mass_desc,
        "case_number": str(clap["case_number"]),
        "act_type": str(clap["act_type"]),
        "primary_type": str(clap["primary_type"]),
        "time": int(raw["time"]),
    }
    # marker.description = "test"
    trip = raw["date"].split("/")
    for i in range(0, len(trip)):
        trip[i] = int(trip[i])
    marker["date"] = int(
        time.mktime(datetime.datetime(trip[2], trip[1], trip[0], 00, 00).timetuple())
    )
    print(marker)
    marker = jsonable_encoder(marker)
    # temp = json.loads(marker)

    new_marker = await db["CrimeMarkers"].insert_one(marker)
    created_marker = await db["CrimeMarkers"].find_one({"id_": new_marker.inserted_id})
    # remove from CrowdModel
    await db["CrowdModel"].delete_one({"_id": raw["_id"]})
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_marker)
