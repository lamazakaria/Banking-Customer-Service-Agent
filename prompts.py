"""
prompts.py - Configuration class for loading and managing agent prompts with MongoDB schema
"""

import yaml
import os
from typing import Dict, Any, Optional
from mongo_jsonschema import SchemaGenerator
from config import MongoSchemaConfig,MongoConfig


# Get the project root directory (parent of backend)
current_file = os.path.abspath(__file__)

# If prompts.py is in project root
project_root = os.path.dirname(current_file)

class PromptConfig:
    """Configuration class for managing agent prompts with MongoDB schema integration"""
    
    def __init__(
        self,
        config_path: str = os.path.join(project_root, "prompts.yaml"),
        schema_path: Optional[str] = None,
        mongo_host: Optional[str] = None,
        mongo_port: Optional[int] = None,
        mongo_database: Optional[str] = None,
        mongo_collections: Optional[list] = None
    ):
        """
        Initialize prompt configuration
        
        Args:
            config_path: Path to prompts.yaml configuration file
            schema_path: Path to MongoDB schema YAML (optional)
            auto_extract_schema: If True, extract schema from MongoDB on initialization
            mongo_host: MongoDB host (for auto extraction)
            mongo_port: MongoDB port (for auto extraction)
            mongo_database: MongoDB database name (for auto extraction)
            mongo_collections: List of collections to extract (for auto extraction)
        """
        self.config_path = config_path
        self.schema_path = schema_path
        self.config = self._load_config()
        
        # Auto-extract schema 
        
        # self._auto_extract_schema(
        #     mongo_host or MongoSchemaConfig.MONGO_HOST,
        #     mongo_port or MongoSchemaConfig.MONGO_PORT,
        #     mongo_database or MongoConfig.DATABASE_NAME,
        #     mongo_collections or MongoSchemaConfig.MONGO_COLLECTIONS
        # )
        
        self.mongodb_schemas = self._load_mongodb_schemas()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load YAML configuration file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML configuration: {e}")
    
    def _auto_extract_schema(
        self,
        host: str,
        port: int,
        database: str,
        collections: Optional[list] = None
    ):
        """Auto-extract schema from MongoDB"""
        if not database:
            raise ValueError("Database name is required for auto schema extraction")
        
        print(f"🔄 Auto-extracting schema from {host}:{port}/{database}...")
        
        try:
            generator = SchemaGenerator(host=host, port=port)
            print(collections)
            schemas = generator.get_schemas(db=database, collections=collections)
            for schema in schemas:
                collection_name = schema.get("title", "unknown_collection")
                print(schema)
            
            # Save to temporary file
            self.schema_path = "mongodb_schemas_auto.yaml"
            schema_data = {
                "database": database,
                "host": host,
                "port": port,
                "collections": schemas
            }
            
            with open(self.schema_path, 'w', encoding='utf-8') as f:
                yaml.dump(schema_data, f, sort_keys=False, default_flow_style=False, allow_unicode=True)
            
            print(f"✅ Schema auto-extracted: {len(schemas)} collections")
            
        except Exception as e:
            print(f"⚠️  Warning: Could not auto-extract schema: {e}")
            self.schema_path = None
    
    def _load_mongodb_schemas(self) -> Dict[str, Any]:
        """Load MongoDB schemas from external file or embedded config"""
        # Try to load from external schema file first
        if self.schema_path and os.path.exists(self.schema_path):
            try:
                with open(self.schema_path, 'r', encoding='utf-8') as f:
                    schema_data = yaml.safe_load(f)
                
                # Handle mongo_jsonschema format
                if 'collections' in schema_data:
                    return schema_data['collections']
                
                return schema_data
                
            except Exception as e:
                print(f"⚠️  Warning: Could not load schema from {self.schema_path}: {e}")
        
        # Fall back to embedded schema in prompts.yaml
        return self.config.get('mongodb_schemas', {})
    
    def _format_mongodb_schema(self,rag_mongo_schema: bool = False) -> str:
        """Format MongoDB schema as a readable string for prompt injection"""
        if not self.mongodb_schemas:
            return "No schema information available."
        
        schema_lines = [
            "="*70,
            "MONGODB DATABASE SCHEMA",
            "="*70,
            ""
        ]
        
        for collection_name, schema_info in self.mongodb_schemas.items():
            if rag_mongo_schema and collection_name == "transactions":
                continue
            schema_lines.append(f"📁 Collection: {collection_name}")
            schema_lines.append("-" * 70)
            
            # Handle mongo_jsonschema format (JSON Schema)
            if isinstance(schema_info, dict):
                # Check if it's JSON Schema format
                if 'properties' in schema_info:
                    schema_lines.append("Fields:")
                    self._format_json_schema_properties(
                        schema_info.get('properties', {}),
                        schema_lines,
                        indent=2
                    )
                    
                    # Show required fields
                    if 'required' in schema_info and schema_info['required']:
                        schema_lines.append(f"\n  Required: {', '.join(schema_info['required'])}")
                
                # Handle embedded format with fields
                elif 'fields' in schema_info:
                    description = schema_info.get('description', '')
                    if description:
                        schema_lines.append(f"Description: {description}")
                    
                    schema_lines.append("Fields:")
                    for field_name, field_info in schema_info['fields'].items():
                        schema_lines.append(f"  • {field_name}: {field_info}")
            
            schema_lines.append("")
        
        schema_lines.append("="*70)
        
        return "\n".join(schema_lines)
    
    def get_orchestrator_prompt(self) -> str:
        """Get orchestrator agent prompt"""
        return self.config['orchestrator_agent']['instruction_prompt']
    
    def get_mcp_tools_prompt(self) -> str:
        """Get MCP tools agent prompt with MongoDB schema"""
        base_prompt = self.config['mcp_tools_agent']['instruction_prompt']
        
        # Format schema
        schema_section = self._format_mongodb_schema()
        
        # Replace placeholder with formatted schema
        return base_prompt.replace('{mongodb_schema}', schema_section)
    
    def get_rag_prompt(self) -> str:
        """Get RAG agent prompt"""
        base_prompt = self.config['rag_agent']['instruction_prompt']
        
        # Format schema
        schema_section = self._format_mongodb_schema(rag_mongo_schema=True)
        
        # Replace placeholder with formatted schema
        return base_prompt.replace('{mongodb_schema}', schema_section)
       
    
    def get_final_response_prompt(self) -> str:
        """Get final response agent prompt"""
        return self.config['final_response_agent']['instruction_prompt']
    
    def get_intent_types(self) -> Dict[str, str]:
        """Get intent type mappings"""
        return self.config['agent_config']['intent_types']
    
    def get_memory_keys(self) -> Dict[str, str]:
        """Get memory key mappings"""
        return self.config['agent_config']['memory_keys']
    
    def get_error_messages(self) -> Dict[str, str]:
        """Get error message templates"""
        return self.config['agent_config']['error_messages']
    
    
    def reload_config(self):
        """Reload configuration from file"""
        self.config = self._load_config()
        self.mongodb_schemas = self._load_mongodb_schemas()
    
    def update_schema_from_file(self, schema_path: str):
        """
        Update MongoDB schema from an external file
        
        Args:
            schema_path: Path to the schema YAML file
        """
        self.schema_path = schema_path
        self.mongodb_schemas = self._load_mongodb_schemas()
        print(f"✅ Schema updated from: {schema_path}")
    
    def extract_and_update_schema(
        self,
        host: str = "localhost",
        port: int = 27017,
        database: str = None,
        collections: Optional[list] = None,
        output_file: str = "mongodb_schemas.yaml"
    ):
        """
        Extract schema from MongoDB and update configuration
        
        Args:
            host: MongoDB host
            port: MongoDB port
            database: Database name
            collections: List of collections (None = all)
            output_file: Output file path
        """
        if not database:
            database = os.getenv("MONGO_DATABASE")
            if not database:
                raise ValueError("Database name is required")
        
        print(f"🔄 Extracting schema from {host}:{port}/{database}...")
        
        try:
            generator = SchemaGenerator(host=host, port=port)
            schemas = generator.get_schemas(db=database, collections=collections)
            
            # Save to file
            schema_data = {
                "database": database,
                "host": host,
                "port": port,
                "collections": schemas
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(
                    schema_data,
                    f,
                    sort_keys=False,
                    default_flow_style=False,
                    allow_unicode=True
                )
            
            # Update current configuration
            self.update_schema_from_file(output_file)
            
            print(f"✅ Schema extracted and updated: {len(schemas)} collections")
            
        except Exception as e:
            print(f"❌ Error extracting schema: {e}")
            raise
    
    def get_schema_for_collection(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """
        Get schema for a specific collection
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Schema dictionary or None if not found
        """
        return self.mongodb_schemas.get(collection_name)
    
    def list_collections(self) -> list:
        """Get list of all collections in schema"""
        return list(self.mongodb_schemas.keys())


# Example usage
if __name__ == "__main__":
    print("="*70)
    print("PROMPT CONFIG - SCHEMA INTEGRATION TEST")
    print("="*70)
    
    # Method 1: Load with existing schema file
    print("\n1️⃣  Loading with existing schema file...")
    try:
        config = PromptConfig(
            config_path="prompts.yaml",
            schema_path="mongodb_schemas.yaml"
        )
        print(f"   ✅ Loaded {len(config.list_collections())} collections")
    except Exception as e:
        print(f"   ⚠️  {e}")


    
    # Display schema info
    print("\n📋 Available Collections:")
    for collection in config.list_collections():
        print(f"  • {collection}")
    
    print("\n" + "="*70)
    print("MCP Tools Prompt Preview (first 500 chars):")
    print("="*70)
    print(config.get_mcp_tools_prompt()[500:]+ "...")