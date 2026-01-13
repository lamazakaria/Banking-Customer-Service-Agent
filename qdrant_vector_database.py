import os
import logging
import uuid
from typing import List, Optional, Any, Dict
from langchain_qdrant import QdrantVectorStore, RetrievalMode
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import VectorParams
from langchain_core.documents import Document
from config import QdrantConfig, EmbeddingsConfig
import pickle
from dotenv import load_dotenv
# ----------------------------
# Logging setup
# ----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

CACHE_IDS_FILE = os.path.expanduser(".cache/ids_cache.pkl")  # expands ~ to home directory
os.makedirs(os.path.dirname(CACHE_IDS_FILE), exist_ok=True)    # ensure folder exists


class QdrantManager:
    def __init__(
        self,
        collection_name: str,
        embedding_config: EmbeddingsConfig = EmbeddingsConfig,
        qdrant_config: QdrantConfig = QdrantConfig,
        cache_ids_file: str = CACHE_IDS_FILE
    ):
        self.collection_name = collection_name
        self.vector_size = embedding_config.MODEL_DIM
        self.cache_ids_file = cache_ids_file
        self.data_dir = qdrant_config.DATA_DIR
        self.embedding_model = embedding_config.MODEL_NAME
        self.distance_metric = qdrant_config.DISTANCE_METRIC
        self.cached_ids = self._load_cached_ids()
        

        # Ensure storage folder exists
        os.makedirs(self.data_dir, exist_ok=True)

        # Initialize Qdrant client
        self.client = QdrantClient(path=self.data_dir)
        self._create_collection_if_not_exists()

        # Initialize embeddings
        self.embeddings = GoogleGenerativeAIEmbeddings(model=self.embedding_model,
                                                       google_api_key=GOOGLE_API_KEY)

        # Initialize Qdrant vector store
        self.vectorstore = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            embedding=self.embeddings,
            retrieval_mode=RetrievalMode.DENSE
        )


    def _load_cached_ids(self) -> set:
        """
        Load cached product IDs from a pickle file.
        Returns an empty set if cache file does not exist.
        """
        if os.path.exists(self.cache_ids_file):
            try:
                with open(self.cache_ids_file, "rb") as f:
                    cached_ids = pickle.load(f)
                logger.info(f"Loaded {len(cached_ids)} cached IDs from '{self.cache_ids_file}'.")
                return cached_ids
            except Exception as e:
                logger.warning(f"Failed to load cache file '{self.cache_ids_file}': {e}")
                return set()
        else:
            logger.info(f"No cache file found at '{self.cache_ids_file}'. Starting with empty cache.")
            return set()

    def _create_collection_if_not_exists(self):
        existing_collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in existing_collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=self.distance_metric)
            )
            logger.info(f"Collection '{self.collection_name}' created.")
        else:
            logger.info(f"Collection '{self.collection_name}' already exists.")

    def add_documents(self, documents: List[Document]):
            """
            Add documents to Qdrant only if their product_id is not in cache.
            """
            docs_to_add = []
            ids_to_add = []

            for doc_id, doc in enumerate(documents):
                pid = self.mongo_id_to_uuid(doc.metadata.get("_id"),  doc_id)
                if pid and pid not in self.cached_ids:
                    docs_to_add.append(doc)
                    ids_to_add.append(pid)

            if docs_to_add:
                self.vectorstore.add_documents(documents=docs_to_add, ids=ids_to_add)
                self._update_cache(ids_to_add)
                logger.info(f"Added {len(docs_to_add)} new documents to collection '{self.collection_name}'.")


    def similarity_search(
            self,
            query: str,
            k: int = 5,
            filter_conditions: Optional[Dict[str, Any]] = None
        ) -> List[Document]:
            """
            Perform similarity search with optional filter conditions.

            filter_conditions example:
            {
                "category": "Deposit",
                "status": "Active"
            }
            """
            qdrant_filter = None
            if filter_conditions:
                must_conditions = []
                for key, value in filter_conditions.items():
                    must_conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value)
                        )
                    )
                qdrant_filter = models.Filter(must=must_conditions)

            return self.vectorstore.similarity_search(query, k=k, filter=qdrant_filter)
    

    def _update_cache(self, new_ids: set):
        """
        Add new IDs to the cache and save to disk.
        """
        self.cached_ids.update(new_ids)
        try:
            with open(self.cache_ids_file, "wb") as f:
                pickle.dump(self.cached_ids, f)
            logger.info(f"Updated cache with {len(new_ids)} new IDs.")
        except Exception as e:
            logger.warning(f"Failed to update cache file '{self.cache_ids_file}': {e}")

    @staticmethod
    def mongo_id_to_uuid(mongo_id: str, chunk_index: int) -> str:
        """Convert MongoDB ObjectId + chunk index to unique UUID."""
        namespace = uuid.NAMESPACE_DNS
        # Combine mongo_id with chunk index for uniqueness
        unique_string = f"{mongo_id}_chunk_{chunk_index}"
        return str(uuid.uuid5(namespace, unique_string))
    

    def close(self):
        """Properly close Qdrant client connection."""
        try:
            if hasattr(self, 'client') and self.client:
                self.client.close()
                logger.info("Qdrant client closed successfully")
        except Exception as e:
            logger.warning(f"Error closing Qdrant client: {e}")
    
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.close()