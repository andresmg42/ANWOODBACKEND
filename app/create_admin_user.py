from sqlmodel import Session,select
from .database import engine,create_db_and_tables
import os
from dotenv import load_dotenv
from .auth import get_password_hash,assign_role_to_user,RoleEnum
from .models import User
from .seed import seed_data


load_dotenv()

USERNAME=os.getenv("SUPERUSER_USERNAME")
PASSWORD=os.getenv("PASSWORD")
EMAIL=os.getenv("EMAIL")
        

def create_super_user(db:Session):
    

    if not USERNAME or not PASSWORD or not EMAIL:
        print('USER DATA IS WRONG')
        return 
    
    existing=db.exec(select(User).where(User.username==USERNAME)).first()

    if existing:
        print('user already exists')
        return
    hashed_password=get_password_hash(PASSWORD)

    user=User(
        username=USERNAME,
        email=EMAIL,
        hashed_password=hashed_password,
    )        

    db.add(user)
    db.commit()
    db.refresh(user)

    assign_role_to_user(user,RoleEnum.ADMIN,db)



if __name__ == "__main__":
    with Session(engine) as db:
        create_db_and_tables()
        seed_data(db)
        create_super_user(db)
        print('super user created succesfully')

        
        

        