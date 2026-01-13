
from qdrant_client.http.models import Distance

class ProductDocumentConfig:
    # Fields to include in the document in order
    DOCUMENT_FIELDS_ORDER = [
        "category",
        "product_name",
        "interest_rate",
        "features",
        "eligibility",
        "fees",
        "faqs"
    ]
    
    # Fields to include as metadata
    METADATA_FIELDS = ["_id","product_id", "status","category"]
    
    # Label overrides (optional)
    FIELD_LABELS = {
        "category": "Category",
        "product_name": "Product Name",
        "interest_rate": "Interest Rate",
        "features": "Features",
        "eligibility": "Eligibility",
        "fees": "Fees",
        "faqs": "FAQs"
    }


class EmbeddingsConfig:
    MODEL_NAME = "models/text-embedding-004"
    MODEL_DIM = 768


class QdrantConfig:
    DATA_DIR = "./qdrant_data"
    CACHE_IDS_FILE = "/.cache/ids_cache.pkl"
    DISTANCE_METRIC = Distance.COSINE


class MongoConfig:
    MONGO_URI = "mongodb://localhost:27017/"
    DATABASE_NAME = "banking_db"


class ModelConfig:
    APP_NAME = "Bank Customer Service"
    MODEL_NAME = "gemini-2.5-flash"
    TEMPERATURE = 0.2



class MongoSchemaConfig:
    MONGO_COLLECTIONS = ["accounts", "customers", "transactions"]
    MONGO_HOST = "localhost"
    MONGO_PORT = 27017