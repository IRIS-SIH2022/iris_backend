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
    crime: str = Field(...)
    time: time = Field(...)
    date: date = Field(...)
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
                "crime": "Assault",
                "time": 1658130003,
                "intensity": "Medium",
            }
        }


class UpdateCrimeData(BaseModel):
    lat: Optional[float]
    lng: Optional[float]
    crime: Optional[str]
    time: Optional[int]
    intensity: Optional[str]

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "lat": "28.614",
                "lng": "77.203",
                "crime": "Assault",
                "time": "1658130003",
                "intensity": "Medium",
            }
        }


@app.post("/marker", response_description="Add new crime marker", response_model=CrimeDataModel)
async def create_marker(crime: CrimeDataModel = Body(...)):
    crime = jsonable_encoder(crime)
    new_crime = await db["CrimeMarkers"].insert_one(crime)
    created_crime = await db["CrimeMarkers"].find_one({"_id": new_crime.inserted_id})
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_crime)


@app.get(
    "/marker", response_description="List all crime markers", response_model=List[CrimeDataModel]
)
async def list_crime_markers():
    students = await db["CrimeMarkers"].find().to_list(100000)
    return students


@app.get(
    "/marker/{id}", response_description="Get a single crime marker", response_model=CrimeDataModel
)
async def show_student(id: str):
    if (crime := await db["CrimeMarkers"].find_one({"_id": id})) is not None:
        return crime

    raise HTTPException(status_code=404, detail=f"Crime {id} not found")


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
                "state": "Delhi",
                "district": "North Delhi",
                "block": "Block 1",
                "geoJSON": {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon",
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
                                                                              ]}},
            }
        }


class UpdateGeoJSONData(BaseModel):
    state: Optional[str]
    district: Optional[str]
    block: Optional[str]
    geoJSON: Optional[dict]

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "state": "Delhi",
                "district": "North Delhi",
                "block": "Block 1",
                "geoJSON": {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon",
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
                                                                              ]}},
            }
        }


@app.post("/area", response_description="Add new area polygon", response_model=GeoJSONModel)
async def create_area(area: GeoJSONModel = Body(...)):
    area = jsonable_encoder(area)
    new_area = await db["GeoJSON"].insert_one(area)
    created_area = await db["GeoJSON"].find_one({"gid": new_area.inserted_id})
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_area)


@app.get(
    "/area", response_description="List all area polygons", response_model=List[GeoJSONModel]
)
async def list_areas():
    areas = await db["GeoJSON"].find().to_list(1000)
    return areas


@app.get(
    "/area/{id}", response_description="Get a single crime marker", response_model=CrimeDataModel
)
async def show_area(id: str):
    if (area := await db["GeoJSON"].find_one({"gid": id})) is not None:
        return area

    raise HTTPException(status_code=404, detail=f"Area {id} not found")


#
# class StudentModel(BaseModel):
#     id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
#     name: str = Field(...)
#     email: EmailStr = Field(...)
#     course: str = Field(...)
#     gpa: float = Field(..., le=4.0)
#
#     class Config:
#         allow_population_by_field_name = True
#         arbitrary_types_allowed = True
#         json_encoders = {ObjectId: str}
#         schema_extra = {
#             "example": {
#                 "name": "Jane Doe",
#                 "email": "jdoe@example.com",
#                 "course": "Experiments, Science, and Fashion in Nanophotonics",
#                 "gpa": "3.0",
#             }
#         }
#
#
# class UpdateStudentModel(BaseModel):
#     name: Optional[str]
#     email: Optional[EmailStr]
#     course: Optional[str]
#     gpa: Optional[float]
#

#
#
# @app.post("/", response_description="Add new student", response_model=StudentModel)
# async def create_student(student: StudentModel = Body(...)):
#     student = jsonable_encoder(student)
#     new_student = await db["students"].insert_one(student)
#     created_student = await db["students"].find_one({"_id": new_student.inserted_id})
#     return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_student)
#
#
# @app.get(
#     "/", response_description="List all students", response_model=List[StudentModel]
# )
# async def list_students():
#     students = await db["students"].find().to_list(1000)
#     return students
#
#
# @app.get(
#     "/{id}", response_description="Get a single student", response_model=StudentModel
# )
# async def show_student(id: str):
#     if (student := await db["students"].find_one({"_id": id})) is not None:
#         return student
#
#     raise HTTPException(status_code=404, detail=f"Student {id} not found")
#
#
# @app.put("/{id}", response_description="Update a student", response_model=StudentModel)
# async def update_student(id: str, student: UpdateStudentModel = Body(...)):
#     student = {k: v for k, v in student.dict().items() if v is not None}
#
#     if len(student) >= 1:
#         update_result = await db["students"].update_one({"_id": id}, {"$set": student})
#
#         if update_result.modified_count == 1:
#             if (
#                     updated_student := await db["students"].find_one({"_id": id})
#             ) is not None:
#                 return updated_student
#
#     if (existing_student := await db["students"].find_one({"_id": id})) is not None:
#         return existing_student
#
#     raise HTTPException(status_code=404, detail=f"Student {id} not found")
#
#
# @app.delete("/{id}", response_description="Delete a student")
# async def delete_student(id: str):
#     delete_result = await db["students"].delete_one({"_id": id})
#
#     if delete_result.deleted_count == 1:
#         return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)
#
#     raise HTTPException(status_code=404, detail=f"Student {id} not found")
