from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import uuid
from datetime import datetime

app = FastAPI(
    title="FastAPI Service",
    description="Documentation de l'API FastAPI",
    version="1.0.0",
    docs_url="/swagger",  # URL pour Swagger UI
    redoc_url="/redoc",   # URL pour ReDoc
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response validation
class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    category: str

class ItemCreate(ItemBase):
    pass

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None

class Item(ItemBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

# In-memory database
items_db: Dict[str, Item] = {}

# Dependency to get database
def get_db():
    return items_db

# CRUD operations
@app.post("/items/", response_model=Item, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate, db: Dict = Depends(get_db)):
    """Create a new item"""
    item_id = str(uuid.uuid4())
    current_time = datetime.now()
    
    item_dict = item.dict()
    db_item = Item(
        **item_dict,
        id=item_id,
        created_at=current_time
    )
    
    db[item_id] = db_item
    return db_item

@app.get("/items/", response_model=List[Item])
def read_items(skip: int = 0, limit: int = 100, db: Dict = Depends(get_db)):
    """Retrieve all items with pagination"""
    items = list(db.values())
    return items[skip: skip + limit]

@app.get("/items/{item_id}", response_model=Item)
def read_item(item_id: str, db: Dict = Depends(get_db)):
    """Retrieve a specific item by ID"""
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Item not found")
    return db[item_id]

@app.put("/items/{item_id}", response_model=Item)
def update_item(item_id: str, item: ItemUpdate, db: Dict = Depends(get_db)):
    """Update an existing item"""
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Item not found")
    
    stored_item = db[item_id]
    update_data = item.dict(exclude_unset=True)
    
    # Update only provided fields
    for field, value in update_data.items():
        setattr(stored_item, field, value)
    
    # Update the timestamp
    stored_item.updated_at = datetime.now()
    
    db[item_id] = stored_item
    return stored_item

@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: str, db: Dict = Depends(get_db)):
    """Delete an item"""
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Item not found")
    
    del db[item_id]
    return None

@app.get("/")
def root():
    """API root endpoint with welcome message"""
    return {"message": "Welcome to the Item Management API"}
