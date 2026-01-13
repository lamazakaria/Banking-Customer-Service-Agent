import logging
from typing import Dict, Union, List
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from pymongo import MongoClient
from config import ProductDocumentConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

ValueType = Union[str, int, float, list]


class MongoLoaderSplitter:
    def __init__(self, db_name: str, collection_name: str, mongo_url: str = "mongodb://localhost:27017/"):
        """
        Initialize the MongoDB loader.

        Args:
            db_name (str): Name of the MongoDB database.
            collection_name (str): Name of the collection to load.
            mongo_url (str, optional): MongoDB connection string. Defaults to localhost.
        """
        self.client = MongoClient(mongo_url)
        self.db = self.client[db_name]
        self.collection_name = collection_name
        logger.info(f"Connected to MongoDB: {db_name}.{collection_name}")

    def get_documents(self) -> List[Dict[str, ValueType]]:
        """Retrieve all documents from the MongoDB collection."""
        logger.info(f"Fetching documents from collection: {self.collection_name}")
        results = list(self.db[self.collection_name].find({}))
        logger.info(f"Retrieved {len(results)} documents from MongoDB")
        return results

    def format_value(self, field: str, value) -> List[str]:
        """
        Format field values into markdown-compatible lines.
        
        Args:
            field (str): Field name
            value: Field value (can be str, int, float, list, etc.)
            
        Returns:
            List[str]: Formatted lines for the field
        """
        lines = []
        label = ProductDocumentConfig.FIELD_LABELS.get(field, field)
        
        if isinstance(value, list) and all(isinstance(i, dict) for i in value):
            lines.append(f"{label}:")
            for item in value:
                for k, v in item.items():
                    lines.append(f"{k.capitalize()}: {v}")
                lines.append("")
        elif isinstance(value, list):
            lines.append(f"{label}:")
            for item in value:
                lines.append(f"- {item}")
        else:
            if field == "interest_rate" and isinstance(value, (int, float)):
                value = f"{value}%"
            lines.append(f"{label}: {value}")
        
        return lines

    def build_metadata(self, product: dict) -> dict:
        """Extract metadata fields from product document."""
        metadata = {k: str(product.get(k, None)) for k in ProductDocumentConfig.METADATA_FIELDS}
        return metadata

    def create_documents(self) -> List[Document]:
        """
        Create LangChain Document objects from MongoDB documents.
        
        Returns:
            List[Document]: List of formatted documents with metadata
        """
        logger.info("Creating LangChain documents from MongoDB data")
        products = self.get_documents()
        documents = []
        
        for idx, product in enumerate(products):
            content_lines = []
            
            for field_idx, field in enumerate(ProductDocumentConfig.DOCUMENT_FIELDS_ORDER):
                if field not in product:
                    continue

                value_lines = self.format_value(field, product[field])

                if field_idx == 0:
                    # Large header → e.g., category
                    content_lines.append(f"# {value_lines[0]}")
                elif field_idx == 1:
                    # Sub-header → e.g., product name
                    content_lines.append(f"## {value_lines[0]}")
                else:
                    content_lines.extend(value_lines)
            
            page_content = "\n".join(content_lines)
            metadata = self.build_metadata(product)
            documents.append(Document(page_content=page_content, metadata=metadata))
            
            logger.debug(f"Created document {idx + 1}/{len(products)}")
        
        logger.info(f"Successfully created {len(documents)} documents")
        return documents

    def generate_chunks(
        self, 
        chunk_size: int = 200, 
        chunk_overlap: int = 50,
        add_headers_to_content: bool = True
    ) -> List[Document]:
        """
        Generate text chunks with proper metadata propagation.
        
        Process:
        1. Split by markdown headers (preserves header context in metadata)
        2. Further split large sections with RecursiveCharacterTextSplitter
        3. Merge header metadata with original document metadata
        4. Optionally prepend headers to each chunk content
        
        Args:
            chunk_size (int): Maximum size for each chunk
            chunk_overlap (int): Overlap between chunks 
            add_headers_to_content (bool): Whether to prepend header context to chunk content
            
        Returns:
            List[Document]: Chunked documents with complete metadata
        """
        logger.info(f"Starting chunk generation (size={chunk_size}, overlap={chunk_overlap}, add_headers={add_headers_to_content})")
        
        # Step 1: Initialize splitters
        headers_to_split_on = [
            ("#", "Header_1"),
            ("##", "Header_2"),
        ]
        
        header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False  # Keep headers initially for context
        )
        
        recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Step 2: Get documents
        documents = self.create_documents()
        logger.info(f"Processing {len(documents)} documents for chunking")
        
        all_chunks = []
        
        for doc_idx, doc in enumerate(documents):
            logger.info(f"Processing document {doc_idx + 1}/{len(documents)}")
            
            # Step 3: Split by headers first
            header_splits = header_splitter.split_text(doc.page_content)
            logger.debug(f"Document split into {len(header_splits)} header-based sections")
            
            # Step 4: Further split each section and merge metadata
            for section in header_splits:
                # Split large sections into smaller chunks
                text_chunks = recursive_splitter.split_text(section.page_content)
                logger.debug(f"Section split into {len(text_chunks)} recursive chunks")
                
                # Merge metadata once per section (all chunks share same headers)
                metadata = {
                    **doc.metadata,  # Original product metadata
                }
                
                # Prepare header prefix once if needed
                if add_headers_to_content:
                    header_prefix = self._build_header_prefix(section.metadata)
                    # Add headers to all chunks at once
                    final_contents = final_contents = [header_prefix + chunk_text if idx != 0 else chunk_text \
                                                       for idx, chunk_text in enumerate(text_chunks)]
                else:
                    final_contents = text_chunks
                
                # Create Document objects for all chunks
                for final_content in final_contents:
                    chunk_doc = Document(
                        page_content=final_content.strip(),
                        metadata=metadata
                    )
                    all_chunks.append(chunk_doc)
        
        logger.info(f"Generated {len(all_chunks)} total chunks from {len(documents)} documents")
        return all_chunks

    @staticmethod
    def _build_header_prefix(header_metadata: dict) -> str:
        """
        Build header prefix string to prepend to chunks.
        
        Args:
            header_metadata (dict): Metadata containing Header_1, Header_2, etc.
            
        Returns:
            str: Header prefix with trailing newlines
        """
        header_lines = []
        
        # Add headers in order (Header_1, Header_2, etc.)
        if 'Header_1' in header_metadata and header_metadata['Header_1']:
            header_lines.append(f"# {header_metadata['Header_1']}")
        
        if 'Header_2' in header_metadata and header_metadata['Header_2']:
            header_lines.append(f"## {header_metadata['Header_2']}")
        
        if header_lines:
            return '\n'.join(header_lines) + '\n\n'
        
        return ''

    @staticmethod
    def _add_headers_to_chunk(text: str, header_metadata: dict) -> str:
        """
        Prepend header context to chunk content.
        
        Args:
            text (str): Chunk text
            header_metadata (dict): Metadata containing Header_1, Header_2, etc.
            
        Returns:
            str: Text with headers prepended
        """
        header_lines = []
        
        # Add headers in order (Header_1, Header_2, etc.)
        if 'Header_1' in header_metadata and header_metadata['Header_1']:
            header_lines.append(f"# {header_metadata['Header_1']}")
        
        if 'Header_2' in header_metadata and header_metadata['Header_2']:
            header_lines.append(f"## {header_metadata['Header_2']}")
        
        if header_lines:
            return '\n'.join(header_lines) + '\n\n' + text
        
        return text

    @staticmethod
    def _strip_markdown_headers(text: str) -> str:
        """
        Remove markdown headers from text while preserving content.
        
        Args:
            text (str): Text potentially containing markdown headers
            
        Returns:
            str: Text with headers removed
        """
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            stripped = line.lstrip()
            # Remove lines that are pure headers (start with # or ##)
            if stripped.startswith('# ') or stripped.startswith('## '):
                continue
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)

    def close(self):
        """Close MongoDB connection."""
        self.client.close()
        logger.info("MongoDB connection closed")


# # Example usage
# if __name__ == "__main__":
#     loader = MongoLoaderSplitter(
#             db_name="banking_db",  
#         collection_name="bank_products",
#         mongo_url="mongodb://localhost:27017/"
#     )
    
#     try:
#         chunks = loader.generate_chunks(chunk_size=200, chunk_overlap=50, add_headers_to_content=True)
        
#         # Display sample chunk
#         if chunks:
#             logger.info(f"\nSample chunk:")
#             logger.info(f"Content:\n{chunks[0].page_content}...")
#             logger.info(f"\nMetadata: {chunks[0].metadata}")
#             print("##############################")
#             logger.info(f"Content:\n{chunks[1].page_content}...")
#             logger.info(f"\nMetadata: {chunks[1].metadata}")
    
#     finally:
#         loader.close()