import asyncio
import datetime
import random
import hashlib
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath('backend'))

from app.database import AsyncSessionLocal
from app.db_models import DailyGuess

async def seed_data():
    date_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    print(f"Seeding dummy stats for date: {date_str}")
    
    async with AsyncSessionLocal() as db:
        for i in range(1, 101): # 100 fake players
            fake_ip = hashlib.sha256(f"fake_player_{i}".encode()).hexdigest()
            
            # Simulate a normal distribution logic roughly 
            # (people are likely to get smaller pools correct)
            db.add(DailyGuess(date_id=date_str, level_id=1, ip_hash=fake_ip, score=random.choices([0, 1], weights=[10, 90])[0]))
            db.add(DailyGuess(date_id=date_str, level_id=2, ip_hash=fake_ip, score=random.choices([0, 1, 2], weights=[10, 30, 60])[0]))
            db.add(DailyGuess(date_id=date_str, level_id=3, ip_hash=fake_ip, score=random.choices([0, 1, 2, 3], weights=[10, 20, 30, 40])[0]))
            db.add(DailyGuess(date_id=date_str, level_id=4, ip_hash=fake_ip, score=random.choices([0, 1, 2, 3, 4], weights=[20, 20, 20, 20, 20])[0]))
            
        await db.commit()
        print("Successfully seeded 100 fake players!")

if __name__ == "__main__":
    asyncio.run(seed_data())
