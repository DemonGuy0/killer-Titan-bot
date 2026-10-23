import requests
from pymongo import MongoClient
from datetime import datetime

from utils.config import MONGO_URI, MONGO_DB_NAME

def migrate_filters():
    print("🔄 Iniciando migración de filtros...")
    
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB_NAME]
    collection = db["Filters"]
    
    print("📥 Obteniendo filtros de la URL externa...")
    url = "https://datafacil.vercel.app/listado.json"
    response = requests.get(url)
    frases = response.json()
    
    print(f"📊 Se encontraron {len(frases)} filtros en la URL")
    
    existing_filters = set(doc["phrase"] for doc in collection.find({}, {"phrase": 1}))
    print(f"📊 Ya existen {len(existing_filters)} filtros en la BD")
    
    new_filters = []
    for frase in frases:
        if frase not in existing_filters:
            new_filters.append({
                "phrase": frase,
                "created_at": datetime.now(),
                "migrated": True
            })
    
    if new_filters:
        collection.insert_many(new_filters)
        print(f"✅ {len(new_filters)} filtros migrados a la BD")
    else:
        print("ℹ️ No hay filtros nuevos que migrar")
    
    total = collection.count_documents({})
    print(f"📈 Total de filtros en BD: {total}")
    
    client.close()
    print("🎉 Migración completada!")

if __name__ == "__main__":
    migrate_filters()
