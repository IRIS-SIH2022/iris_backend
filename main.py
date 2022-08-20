import os
from fastapi import FastAPI, Body, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, EmailStr, Json
from bson import ObjectId
from typing import Optional, List
import motor.motor_asyncio
from dotenv import load_dotenv
from datetime import date, datetime, time, timedelta
import json

load_dotenv()
app = FastAPI()
client = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGODB_URL"])
db = client.Gotham



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
    act: str = Field(...)
    station_id: int = Field(...)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "lat": 28.614,
                "lng": 77.203,
                "case_number": "asdf",
                "time": 1658130003,
                "date": 1658130003,
                "primary_type": "CRIME",
                "description": "description of crime",
                "act": "Pranav soni act of sexual deviance",
                "station_id": 123,
            }
        }


class UpdateCrimeData(BaseModel):
    lat: Optional[float]
    lng: Optional[float]
    time: Optional[int]
    date: Optional[int]
    primary_type: Optional[str]
    description: Optional[str]
    act: Optional[str]
    station_id: Optional[int]


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


@app.get(
    "/marker/get_all",
    response_description="List all crime markers",
    response_model=List[CrimeDataModel],
)
async def list_crime_markers():
    all_crime = await db["CrimeMarkers"].find().to_list(100000)
    return all_crime


@app.get(
    "/marker/id/{id}",
    response_description="Get a single crime marker by id",
    response_model=CrimeDataModel,
)
async def show_marker(id: str):
    if (crime := await db["CrimeMarkers"].find_one({"_id": id})) is not None:
        return crime
    raise HTTPException(status_code=404, detail=f"Crime {id} not found")


@app.get(
    "/marker/case/{case_number}",
    response_description="Get a single crime marker by case number",
    response_model=CrimeDataModel,
)
async def show_marker(case_number: str):
    if (
        crime := await db["CrimeMarkers"].find_one({"case_number": case_number})
    ) is not None:
        return crime
    raise HTTPException(status_code=404, detail=f"Crime {case_number} not found")


@app.get(
    "/marker/type/{primary_type}",
    response_description="Get all crime markers by primary type",
    response_model=List[CrimeDataModel],
)
async def list_crime_markers_type(primary_type: str):
    all_crime = (
        await db["CrimeMarkers"].find({"primary_type": primary_type}).to_list(100000)
    )
    return all_crime


@app.get(
    "/marker/type/{primary_type}",
    response_description="Get all crime markers by primary type",
    response_model=List[CrimeDataModel],
)
async def list_crime_markers_by_type(primary_type: str):
    all_crime = (
        await db["CrimeMarkers"].find({"primary_type": primary_type}).to_list(100000)
    )
    return all_crime


class GeoJSONModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="gid")
    type: str = Field(...)
    station_id: int = Field(...)
    name: str = Field(...)
    district: str = Field(...)
    geoJSON: dict = Field(...)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "type": "Major crime",
                "district": "North Delhi",
                "station_id": 123,
                "geoJSON": {
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
    station_id: Optional[str]
    geoJSON: Optional[dict]


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
    "/area/{id}",
    response_description="Get a single crime marker",
    response_model=CrimeDataModel,
)
async def show_area(id: str):
    if (area := await db["GeoJSON"].find_one({"gid": id})) is not None:
        return area

    raise HTTPException(status_code=404, detail=f"Area {id} not found")

