#!/usr/bin/env python3
"""
Sentiment Analysis Script for Azure ML Pipeline with Table Storage

This script performs sentiment analysis on JSON data using HuggingFace transformers.
It reads data from Azure Blob Storage, processes it, and writes results to Azure Table Storage.

Author: AI Assistant
Date: 2025-06-02
"""
import sys
import os
import json
import logging
import argparse
from typing import Dict, List, Any
from pathlib import Path
from datetime import datetime
import uuid

import pandas as pd
import numpy as np
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
from azure.storage.blob import BlobServiceClient
from azure.data.tables import TableServiceClient, TableEntity
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceExistsError
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """
    A class to perform sentiment analysis on text data using HuggingFace models.
    
    This class handles model loading, text preprocessing, batch processing,
    and result formatting for Azure ML pipeline integration.
    """
    
    def __init__(self, model_name: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"):
        """
        Initialize the sentiment analyzer with a specified model.
        
        Args:
            model_name (str): HuggingFace model identifier for sentiment analysis
        """
        self.model_name = model_name
        self.sentiment_pipeline = None
        self.tokenizer = None
        self.model = None
        
        logger.info(f"Initializing SentimentAnalyzer with model: {model_name}")
        self._load_model()
    
    def _load_model(self) -> None:
        """Load the sentiment analysis model and tokenizer."""
        try:
            # Load tokenizer and model explicitly for better control
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            
            # Create pipeline
            self.sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model=self.model,
                tokenizer=self.tokenizer,
                top_k=None,  # Return all scores (replaces deprecated return_all_scores=True)
                device=-1  # Use CPU for compatibility
            )
            
            logger.info("Model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise
    
    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text for sentiment analysis.
        
        Args:
            text (str): Raw text to preprocess
            
        Returns:
            str: Preprocessed text
        """
        if not isinstance(text, str):
            text = str(text)
        
        # Basic preprocessing
        text = text.strip()
        
        # Truncate if too long (model-specific limits)
        max_length = self.tokenizer.model_max_length - 2  # Account for special tokens
        if len(text) > max_length:
            text = text[:max_length]
            logger.warning(f"Text truncated to {max_length} characters")
        
        return text
    
    def analyze_sentiment(self, texts: List[str], batch_size: int = 16) -> List[Dict[str, Any]]:
        """
        Analyze sentiment for a list of texts.
        
        Args:
            texts (List[str]): List of texts to analyze
            batch_size (int): Batch size for processing
            
        Returns:
            List[Dict[str, Any]]: List of sentiment analysis results
        """
        results = []
        
        # Process texts in batches
        for i in tqdm(range(0, len(texts), batch_size), desc="Processing batches"):
            batch = texts[i:i + batch_size]
            
            try:
                # Preprocess batch
                processed_batch = [self.preprocess_text(text) for text in batch]
                
                # Run sentiment analysis
                batch_results = self.sentiment_pipeline(processed_batch)
                
                # Format results
                for j, result in enumerate(batch_results):
                    formatted_result = {
                        'text': batch[j],
                        'sentiment_scores': result,
                        'predicted_sentiment': max(result, key=lambda x: x['score'])['label'],
                        'confidence': max(result, key=lambda x: x['score'])['score']
                    }
                    results.append(formatted_result)
                    
            except Exception as e:
                logger.error(f"Error processing batch {i//batch_size + 1}: {str(e)}")
                # Add error results for failed batch
                for text in batch:
                    results.append({
                        'text': text,
                        'sentiment_scores': [],
                        'predicted_sentiment': 'ERROR',
                        'confidence': 0.0,
                        'error': str(e)
                    })
        
        return results


class AzureStorageHandler:
    """Handle Azure Blob Storage operations for data input."""
    
    def __init__(self, storage_account_name: str, container_name: str = "data"):
        """
        Initialize Azure Storage handler.
        
        Args:
            storage_account_name (str): Azure Storage Account name
            container_name (str): Blob container name
        """
        self.storage_account_name = storage_account_name
        self.container_name = container_name
        
        # Use DefaultAzureCredential for authentication (works with managed identity in Azure ML)
        logger.info("Initializing Azure Storage authentication...")
        logger.info(f"Storage Account: {storage_account_name}")
        logger.info(f"Container: {self.container_name}")
        
        # Step 1: Initialize credential
        logger.info("Step 1: Initializing DefaultAzureCredential...")
        credential = DefaultAzureCredential()
        account_url = f"https://{storage_account_name}.blob.core.windows.net"
        logger.info(f"Account URL: {account_url}")
        
        # Step 2: Create BlobServiceClient
        logger.info("Step 2: Creating BlobServiceClient...")
        self.blob_service_client = BlobServiceClient(
            account_url=account_url,
            credential=credential
        )
        
        logger.info("✅ Azure Storage client initialized successfully")
        logger.info(f"Initialized Azure Storage handler for account: {storage_account_name}")
    
    def download_json_data(self, blob_name: str) -> List[Dict[str, Any]]:
        """
        Download JSON data from Azure Blob Storage.
        
        Args:
            blob_name (str): Name of the blob to download
            
        Returns:
            List[Dict[str, Any]]: Parsed JSON data
        """
        logger.info(f"Downloading {blob_name} from Azure Blob Storage...")
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_name
        )
        
        # Download blob content
        blob_data = blob_client.download_blob().readall()
        
        # Parse JSON
        json_data = json.loads(blob_data.decode('utf-8'))
        
        logger.info(f"✅ Successfully downloaded {len(json_data)} records from {blob_name}")
        return json_data


class AzureTableStorageHandler:
    """Handle Azure Table Storage operations for sentiment results."""
    
    def __init__(self, storage_account_name: str, table_name: str = "SentimentResults"):
        """
        Initialize Azure Table Storage handler.
        
        Args:
            storage_account_name (str): Azure Storage Account name
            table_name (str): Table name for storing results
        """
        self.storage_account_name = storage_account_name
        self.table_name = table_name
        
        # Use DefaultAzureCredential for authentication
        logger.info("Initializing Azure Table Storage authentication...")
        logger.info(f"Storage Account: {storage_account_name}")
        logger.info(f"Table: {self.table_name}")
        
        credential = DefaultAzureCredential()
        account_url = f"https://{storage_account_name}.table.core.windows.net"
        logger.info(f"Table Account URL: {account_url}")
        
        # Create TableServiceClient
        self.table_service_client = TableServiceClient(
            endpoint=account_url,
            credential=credential
        )
        
        # Create table if it doesn't exist
        self._create_table_if_not_exists()
        
        logger.info("✅ Azure Table Storage client initialized successfully")
    
    def _create_table_if_not_exists(self) -> None:
        """Create the table if it doesn't exist."""
        try:
            self.table_service_client.create_table(table_name=self.table_name)
            logger.info(f"✅ Created table: {self.table_name}")
        except ResourceExistsError:
            logger.info(f"✅ Table already exists: {self.table_name}")
        except Exception as e:
            logger.error(f"Failed to create table: {str(e)}")
            raise
    
    def _prepare_entity_for_table(self, record: Dict[str, Any], record_id: int) -> TableEntity:
        """
        Prepare a record for insertion into Azure Table Storage.
        
        Args:
            record (Dict[str, Any]): Original record with sentiment analysis
            record_id (int): Record identifier
            
        Returns:
            TableEntity: Entity ready for table insertion
        """
        # Generate partition key and row key
        # Using date as partition key for efficient querying
        partition_key = datetime.now().strftime("%Y-%m-%d")
        row_key = f"{record_id:06d}_{str(uuid.uuid4())[:8]}"
        
        # Prepare entity - flatten nested structures for table storage
        entity = TableEntity()
        entity["PartitionKey"] = partition_key
        entity["RowKey"] = row_key
        
        # Original data fields
        entity["OriginalId"] = record.get("id", record_id)
        entity["Text"] = record.get("text", "")[:32000]  # Table storage limit
        entity["Category"] = record.get("category", "")
        entity["Source"] = record.get("source", "")
        
        # Sentiment analysis results
        sentiment_analysis = record.get("sentiment_analysis", {})
        entity["PredictedSentiment"] = sentiment_analysis.get("predicted_sentiment", "")
        entity["Confidence"] = float(sentiment_analysis.get("confidence", 0.0))
        
        # Store all scores as JSON string (since table storage doesn't support nested objects)
        all_scores = sentiment_analysis.get("all_scores", [])
        entity["AllScoresJson"] = json.dumps(all_scores)
        
        # Processing metadata
        processing_metadata = record.get("processing_metadata", {})
        entity["ModelUsed"] = processing_metadata.get("model_used", "")
        entity["ProcessedAt"] = processing_metadata.get("processed_at", datetime.now().isoformat())
        entity["RecordId"] = processing_metadata.get("record_id", record_id)
        
        # Additional metadata
        entity["InsertedAt"] = datetime.now().isoformat()
        entity["BatchId"] = str(uuid.uuid4())
        
        return entity
    
    def insert_sentiment_results(self, results: List[Dict[str, Any]]) -> None:
        """
        Insert sentiment analysis results into Azure Table Storage.
        
        Args:
            results (List[Dict[str, Any]]): List of sentiment analysis results
        """
        logger.info(f"Inserting {len(results)} sentiment results into table: {self.table_name}")
        
        table_client = self.table_service_client.get_table_client(table_name=self.table_name)
        
        successful_inserts = 0
        failed_inserts = 0
        
        for i, result in enumerate(tqdm(results, desc="Inserting records")):
            try:
                # Prepare entity for table storage
                entity = self._prepare_entity_for_table(result, i)
                
                # Insert entity
                table_client.create_entity(entity=entity)
                successful_inserts += 1
                
            except Exception as e:
                logger.error(f"Failed to insert record {i}: {str(e)}")
                failed_inserts += 1
        
        logger.info(f"✅ Table insertion complete:")
        logger.info(f"   • Successful: {successful_inserts}")
        logger.info(f"   • Failed: {failed_inserts}")
        
        if failed_inserts > 0:
            logger.warning(f"⚠️  {failed_inserts} records failed to insert")
    
    def query_results_summary(self) -> Dict[str, Any]:
        """
        Query the table to get a summary of sentiment results.
        
        Returns:
            Dict[str, Any]: Summary statistics
        """
        try:
            table_client = self.table_service_client.get_table_client(table_name=self.table_name)
            
            # Query all entities (be careful with large datasets)
            entities = list(table_client.list_entities())
            
            if not entities:
                return {"total_records": 0, "sentiment_distribution": {}}
            
            # Calculate sentiment distribution
            sentiment_counts = {}
            for entity in entities:
                sentiment = entity.get("PredictedSentiment", "unknown")
                sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
            
            summary = {
                "total_records": len(entities),
                "sentiment_distribution": sentiment_counts,
                "latest_batch_time": max([entity.get("ProcessedAt", "") for entity in entities]),
                "table_name": self.table_name
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to query table summary: {str(e)}")
            return {"error": str(e)}


def main():
    """Main function to run sentiment analysis pipeline with Table Storage output."""
    parser = argparse.ArgumentParser(description="Azure ML Sentiment Analysis Pipeline with Table Storage")
    parser.add_argument("--input-data", 
                       default='sentiment_data.json',
                       help="Input data blob name")
    parser.add_argument("--table-name", 
                       default='SentimentResults',
                       help="Azure Table Storage table name")
    parser.add_argument("--storage-account", 
                       required=True,
                       help="Azure Storage Account name")
    parser.add_argument("--container-name", 
                       default='data',
                       help="Storage container name for input data")
    parser.add_argument("--model-name", 
                       default='cardiffnlp/twitter-roberta-base-sentiment-latest', 
                       help="HuggingFace model name")
    parser.add_argument("--batch-size", type=int, 
                       default=16, 
                       help="Batch size for processing")
    parser.add_argument("--text-field", 
                       default='text', 
                       help="JSON field containing text to analyze")
    
    args = parser.parse_args()
    
    logger.info("Starting sentiment analysis pipeline with Table Storage")
    logger.info(f"Input: {args.input_data}")
    logger.info(f"Table: {args.table_name}")
    logger.info(f"Model: {args.model_name}")
    
    try:
        # Initialize components
        analyzer = SentimentAnalyzer(model_name=args.model_name)
        storage_handler = AzureStorageHandler(
            storage_account_name=args.storage_account,
            container_name=args.container_name
        )
        table_handler = AzureTableStorageHandler(
            storage_account_name=args.storage_account,
            table_name=args.table_name
        )
        
        # Download input data
        logger.info("Downloading input data...")
        input_data = storage_handler.download_json_data(args.input_data)
        
        # Extract texts for analysis
        texts = []
        for record in input_data:
            if args.text_field in record:
                texts.append(record[args.text_field])
            else:
                logger.warning(f"Text field '{args.text_field}' not found in record")
                texts.append("")
        
        logger.info(f"Extracted {len(texts)} texts for analysis")
        
        # Perform sentiment analysis
        logger.info("Performing sentiment analysis...")
        sentiment_results = analyzer.analyze_sentiment(texts, batch_size=args.batch_size)
        
        # Combine original data with sentiment results
        enriched_data = []
        for i, (original_record, sentiment_result) in enumerate(zip(input_data, sentiment_results)):
            enriched_record = {
                **original_record,
                'sentiment_analysis': {
                    'predicted_sentiment': sentiment_result['predicted_sentiment'],
                    'confidence': sentiment_result['confidence'],
                    'all_scores': sentiment_result['sentiment_scores']
                },
                'processing_metadata': {
                    'model_used': args.model_name,
                    'processed_at': pd.Timestamp.now().isoformat(),
                    'record_id': i
                }
            }
            enriched_data.append(enriched_record)
        
        # Insert results into Table Storage
        logger.info("Inserting results into Table Storage...")
        table_handler.insert_sentiment_results(enriched_data)
        
        # Generate and display summary statistics
        logger.info("Generating summary statistics...")
        summary = table_handler.query_results_summary()
        
        logger.info("Sentiment Analysis Summary:")
        logger.info(f"  Total records processed: {len(enriched_data)}")
        logger.info(f"  Total records in table: {summary.get('total_records', 0)}")
        
        sentiment_distribution = summary.get('sentiment_distribution', {})
        if sentiment_distribution:
            logger.info("  Sentiment distribution:")
            total = sum(sentiment_distribution.values())
            for sentiment, count in sentiment_distribution.items():
                percentage = (count / total * 100) if total > 0 else 0
                logger.info(f"    {sentiment}: {count} ({percentage:.1f}%)")
        
        logger.info(f"✅ Pipeline completed successfully! Results stored in table: {args.table_name}")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()
