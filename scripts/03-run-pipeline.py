#!/usr/bin/env python3
"""
Azure ML Pipeline Submission Script

This script submits and monitors the sentiment analysis pipeline job in Azure Machine Learning.
It handles authentication, pipeline submission, job monitoring, and result retrieval.

Author: AI Assistant
Date: 2025-05-30
"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path
from typing import Optional, Dict, Any

from azure.ai.ml import MLClient
from azure.ai.ml.entities import Job
from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential
from azure.core.exceptions import ResourceNotFoundError
import yaml

# Import environment utilities
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from env_utils import get_env, get_env_int, get_env_bool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AzureMLPipelineManager:
    """
    Manages Azure ML pipeline submission, monitoring, and result retrieval.
    
    This class handles the complete lifecycle of pipeline jobs including
    authentication, submission, monitoring, and cleanup operations.
    """
    
    def __init__(self, subscription_id: str, resource_group: str, workspace_name: str):
        """
        Initialize the Azure ML Pipeline Manager.
        
        Args:
            subscription_id (str): Azure subscription ID
            resource_group (str): Azure resource group name
            workspace_name (str): Azure ML workspace name
        """
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.workspace_name = workspace_name
        self.ml_client = None
        
        logger.info(f"Initializing Azure ML client for workspace: {workspace_name}")
        self._authenticate()
    
    def _authenticate(self) -> None:
        """Authenticate with Azure and create ML client."""
        try:
            # Try DefaultAzureCredential first (works with managed identity, CLI, etc.)
            credential = DefaultAzureCredential()
            
            # Create ML client
            self.ml_client = MLClient(
                credential=credential,
                subscription_id=self.subscription_id,
                resource_group_name=self.resource_group,
                workspace_name=self.workspace_name
            )
            
            # Test the connection
            workspace = self.ml_client.workspaces.get(self.workspace_name)
            logger.info(f"Successfully connected to workspace: {workspace.display_name}")
            
        except Exception as e:
            logger.warning(f"DefaultAzureCredential failed: {str(e)}")
            logger.info("Falling back to InteractiveBrowserCredential...")
            
            try:
                # Fallback to interactive browser authentication
                credential = InteractiveBrowserCredential()
                
                self.ml_client = MLClient(
                    credential=credential,
                    subscription_id=self.subscription_id,
                    resource_group_name=self.resource_group,
                    workspace_name=self.workspace_name
                )
                
                # Test the connection
                workspace = self.ml_client.workspaces.get(self.workspace_name)
                logger.info(f"Successfully connected to workspace: {workspace.display_name}")
                
            except Exception as e:
                logger.error(f"Authentication failed: {str(e)}")
                raise
    
    def validate_resources(self) -> Dict[str, bool]:
        """
        Validate that required Azure ML resources exist.
        
        Returns:
            Dict[str, bool]: Validation results for each resource
        """
        validation_results = {
            'workspace': False,
            'compute': False,
            'datastore': False
        }
        
        try:
            # Check workspace
            workspace = self.ml_client.workspaces.get(self.workspace_name)
            validation_results['workspace'] = True
            logger.info(f"✓ Workspace '{self.workspace_name}' exists")
            
            # Check compute cluster
            try:
                compute = self.ml_client.compute.get("sentiment-cluster")
                validation_results['compute'] = True
                logger.info(f"✓ Compute cluster 'sentiment-cluster' exists (State: {compute.provisioning_state})")
            except ResourceNotFoundError:
                logger.warning("✗ Compute cluster 'sentiment-cluster' not found")
            
            # Check default datastore
            try:
                datastore = self.ml_client.datastores.get("workspaceblobstore")
                validation_results['datastore'] = True
                logger.info(f"✓ Datastore 'workspaceblobstore' exists")
            except ResourceNotFoundError:
                logger.warning("✗ Datastore 'workspaceblobstore' not found")
                
        except Exception as e:
            logger.error(f"Resource validation failed: {str(e)}")
        
        return validation_results
    
    def create_or_update_environment(self, environment_file: str) -> str:
        """
        Create or update the Azure ML environment from conda file.
        
        Args:
            environment_file (str): Path to the conda environment file
            
        Returns:
            str: Environment name and version
        """
        try:
            from azure.ai.ml.entities import Environment
            
            # Read environment file
            with open(environment_file, 'r') as f:
                env_config = yaml.safe_load(f)
            
            env_name = "sentiment-analysis-env"
            env_version = "1.0.0"
            
            # Create environment
            environment = Environment(
                name=env_name,
                version=env_version,
                description="Sentiment analysis environment with HuggingFace transformers",
                conda_file=environment_file,
                image="mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu20.04:latest"
            )
            
            # Create or update environment
            env_result = self.ml_client.environments.create_or_update(environment)
            logger.info(f"Environment '{env_name}:{env_version}' created/updated successfully")
            
            return f"{env_name}:{env_version}"
            
        except Exception as e:
            logger.error(f"Failed to create environment: {str(e)}")
            raise
    
    def generate_pipeline_from_template(self, template_file: str, output_file: str) -> str:
        """
        Generate pipeline YAML from template with environment variable substitution.
        
        Args:
            template_file (str): Path to the pipeline template file
            output_file (str): Path to write the generated pipeline file
            
        Returns:
            str: Path to the generated pipeline file
        """
        try:
            # Import environment utilities for variable resolution
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
            from env_utils import EnvironmentManager
            env_manager = EnvironmentManager()
            
            # Read template file
            with open(template_file, 'r') as f:
                template_content = f.read()
            
            # Define template variables with their environment variable sources
            template_vars = {
                'PIPELINE_DISPLAY_NAME': env_manager.get_env('PIPELINE_DISPLAY_NAME', 'Sentiment Analysis Pipeline with Table Storage'),
                'PIPELINE_DESCRIPTION': env_manager.get_env('PIPELINE_DESCRIPTION', 'End-to-end sentiment analysis pipeline using HuggingFace transformers with Azure Table Storage output'),
                'PIPELINE_EXPERIMENT_NAME': env_manager.get_env('PIPELINE_EXPERIMENT_NAME', 'sentiment-analysis-experiment'),
                'AZURE_COMPUTE_NAME': env_manager.get_env('AZURE_COMPUTE_NAME', 'sentiment-cluster'),
                'ML_DEFAULT_DATASTORE': env_manager.get_env('ML_DEFAULT_DATASTORE', 'workspaceblobstore'),
                'ML_ENVIRONMENT_NAME': env_manager.get_env('ML_ENVIRONMENT_NAME', 'sentiment-analysis-env'),
                'ML_ENVIRONMENT_VERSION': env_manager.get_env('ML_ENVIRONMENT_VERSION', '1.0.0'),
                'INPUT_DATA_FILE': env_manager.get_env('INPUT_DATA_FILE', 'sentiment_data.json'),
                'OUTPUT_TABLE_NAME': env_manager.get_env('OUTPUT_TABLE_NAME', 'SentimentResults'),
                'AZURE_STORAGE_ACCOUNT_NAME': env_manager.get_env('AZURE_STORAGE_ACCOUNT_NAME'),
                'STORAGE_CONTAINER_NAME': env_manager.get_env('STORAGE_CONTAINER_NAME'),
                'ML_MODEL_NAME': env_manager.get_env('ML_MODEL_NAME', 'cardiffnlp/twitter-roberta-base-sentiment-latest'),
                'ML_BATCH_SIZE': env_manager.get_env('ML_BATCH_SIZE', '16'),
                'ML_TEXT_FIELD': env_manager.get_env('ML_TEXT_FIELD', 'text'),
                'PYTHONPATH': env_manager.get_env('PYTHONPATH', '/mnt/azureml/cr/j/src'),
                'TRANSFORMERS_CACHE': env_manager.get_env('TRANSFORMERS_CACHE', '/tmp/transformers_cache'),
                'HF_HOME': env_manager.get_env('HF_HOME', '/tmp/huggingface_cache'),
                'HF_DATASETS_CACHE': env_manager.get_env('HF_DATASETS_CACHE', '/tmp/datasets_cache')
            }
            
            # Substitute template variables
            generated_content = template_content
            for var_name, var_value in template_vars.items():
                placeholder = f'{{{var_name}}}'
                generated_content = generated_content.replace(placeholder, str(var_value))
            
            # Write generated pipeline file
            with open(output_file, 'w') as f:
                f.write(generated_content)
            
            logger.info(f"Generated pipeline file: {output_file}")
            logger.info("Template variables substituted:")
            for var_name, var_value in template_vars.items():
                logger.info(f"  {var_name}: {var_value}")
            
            return output_file
            
        except Exception as e:
            logger.error(f"Failed to generate pipeline from template: {str(e)}")
            raise
    
    def submit_pipeline(self, pipeline_file: str, **kwargs) -> Job:
        """
        Submit the pipeline job to Azure ML.
        
        Args:
            pipeline_file (str): Path to the pipeline YAML file
            **kwargs: Additional parameters to override pipeline inputs
            
        Returns:
            Job: The submitted pipeline job
        """
        try:
            from azure.ai.ml import load_job
            
            # Load pipeline job from YAML
            pipeline_job = load_job(source=pipeline_file)
            
            # Override inputs if provided
            if kwargs:
                logger.info("Overriding pipeline inputs:")
                for key, value in kwargs.items():
                    if hasattr(pipeline_job.inputs, key):
                        setattr(pipeline_job.inputs, key, value)
                        logger.info(f"  {key}: {value}")
            
            # Submit the job
            logger.info("Submitting pipeline job...")
            submitted_job = self.ml_client.jobs.create_or_update(pipeline_job)
            
            logger.info(f"Pipeline job submitted successfully!")
            logger.info(f"Job name: {submitted_job.name}")
            logger.info(f"Job ID: {submitted_job.id}")
            logger.info(f"Studio URL: {submitted_job.studio_url}")
            
            return submitted_job
            
        except Exception as e:
            logger.error(f"Failed to submit pipeline: {str(e)}")
            raise
    
    def monitor_job(self, job: Job, poll_interval: int = 30) -> Job:
        """
        Monitor the pipeline job until completion.
        
        Args:
            job (Job): The pipeline job to monitor
            poll_interval (int): Polling interval in seconds
            
        Returns:
            Job: The completed job with final status
        """
        logger.info(f"Monitoring job: {job.name}")
        logger.info(f"Studio URL: {job.studio_url}")
        
        try:
            while True:
                # Get current job status
                current_job = self.ml_client.jobs.get(job.name)
                status = current_job.status
                
                logger.info(f"Job status: {status}")
                
                # Check if job is complete
                if status in ["Completed", "Failed", "Canceled"]:
                    break
                
                # Wait before next poll
                time.sleep(poll_interval)
            
            # Get final job details
            final_job = self.ml_client.jobs.get(job.name)
            
            if final_job.status == "Completed":
                logger.info("✓ Pipeline job completed successfully!")
                self._log_job_outputs(final_job)
            elif final_job.status == "Failed":
                logger.error("✗ Pipeline job failed!")
                self._log_job_errors(final_job)
            else:
                logger.warning(f"Pipeline job ended with status: {final_job.status}")
            
            return final_job
            
        except KeyboardInterrupt:
            logger.info("Monitoring interrupted by user")
            return self.ml_client.jobs.get(job.name)
        except Exception as e:
            logger.error(f"Error monitoring job: {str(e)}")
            raise
    
    def _log_job_outputs(self, job: Job) -> None:
        """Log job outputs and metrics."""
        try:
            logger.info("Job Outputs:")
            if hasattr(job, 'outputs') and job.outputs:
                for output_name, output_value in job.outputs.items():
                    logger.info(f"  {output_name}: {output_value}")
            else:
                logger.info("  No outputs available")
                
        except Exception as e:
            logger.warning(f"Could not retrieve job outputs: {str(e)}")
    
    def _log_job_errors(self, job: Job) -> None:
        """Log job errors and failure details."""
        try:
            logger.error("Job Error Details:")
            if hasattr(job, 'error') and job.error:
                logger.error(f"  Error: {job.error}")
            
            # Try to get child job details for more specific errors
            try:
                child_jobs = self.ml_client.jobs.list(parent_job_name=job.name)
                for child_job in child_jobs:
                    if child_job.status == "Failed":
                        logger.error(f"  Failed step: {child_job.display_name}")
                        if hasattr(child_job, 'error') and child_job.error:
                            logger.error(f"    Error: {child_job.error}")
            except:
                pass
                
        except Exception as e:
            logger.warning(f"Could not retrieve job error details: {str(e)}")
    
    def download_outputs(self, job: Job, output_dir: str = "./outputs") -> None:
        """
        Download job outputs to local directory.
        
        Args:
            job (Job): The completed job
            output_dir (str): Local directory to save outputs
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            logger.info(f"Downloading job outputs to: {output_path.absolute()}")
            
            # Download outputs
            if hasattr(job, 'outputs') and job.outputs:
                for output_name, output_value in job.outputs.items():
                    try:
                        self.ml_client.jobs.download(
                            name=job.name,
                            output_name=output_name,
                            download_path=output_path
                        )
                        logger.info(f"✓ Downloaded output: {output_name}")
                    except Exception as e:
                        logger.warning(f"Could not download {output_name}: {str(e)}")
            else:
                logger.info("No outputs to download")
                
        except Exception as e:
            logger.error(f"Failed to download outputs: {str(e)}")


def main():
    """Main function to submit and monitor the sentiment analysis pipeline."""
    parser = argparse.ArgumentParser(description="Submit Azure ML Sentiment Analysis Pipeline")
    
    # Required arguments (with environment variable defaults)
    parser.add_argument("--subscription-id", 
                       default=get_env('AZURE_SUBSCRIPTION_ID'),
                       help="Azure subscription ID")
    parser.add_argument("--resource-group", 
                       default=get_env('AZURE_RESOURCE_GROUP_NAME'),
                       help="Azure resource group name")
    parser.add_argument("--workspace-name", 
                       default=get_env('AZURE_ML_WORKSPACE_NAME'),
                       help="Azure ML workspace name")
    
    # Pipeline configuration
    parser.add_argument("--pipeline-file", default="pipelines/sentiment_pipeline.yml.generated", 
                       help="Path to pipeline YAML file")
    parser.add_argument("--pipeline-template-file", default="pipelines/sentiment_pipeline.yml.template", 
                       help="Path to pipeline YAML file")
    parser.add_argument("--environment-file", default="environment.yml", 
                       help="Path to conda environment file")
    
    # Pipeline inputs (optional overrides)
    parser.add_argument("--input-data", help="Override input data path")
    parser.add_argument("--storage-account", help="Override storage account name")
    parser.add_argument("--model-name", help="Override HuggingFace model name")
    parser.add_argument("--batch-size", type=int, help="Override batch size")
    
    # Execution options
    parser.add_argument("--validate-only", action="store_true", 
                       help="Only validate resources, don't submit pipeline")
    parser.add_argument("--no-monitor", action="store_true", 
                       help="Submit pipeline but don't monitor execution")
    parser.add_argument("--download-outputs", action="store_true", 
                       help="Download outputs after completion")
    parser.add_argument("--poll-interval", type=int, default=30, 
                       help="Job monitoring poll interval in seconds")
    
    args = parser.parse_args()
    
    try:
        # Initialize pipeline manager
        pipeline_manager = AzureMLPipelineManager(
            subscription_id=args.subscription_id,
            resource_group=args.resource_group,
            workspace_name=args.workspace_name
        )
        
        # Validate resources
        logger.info("Validating Azure ML resources...")
        validation_results = pipeline_manager.validate_resources()
        
        if not all(validation_results.values()):
            logger.warning("Some resources are missing. Pipeline may fail.")
            if args.validate_only:
                sys.exit(1)
        
        if args.validate_only:
            logger.info("Validation complete. Exiting.")
            return
        
        # Create/update environment
        logger.info("Creating/updating Azure ML environment...")
        env_name = pipeline_manager.create_or_update_environment(args.environment_file)
        
        if os.path.exists(args.pipeline_file):
            logger.info(f"Deleting previous generate pipeline file: {args.pipeline_file}")
            os.remove(args.pipeline_file)
        
        # Generate pipeline file from template
        if os.path.exists(args.pipeline_template_file):
            logger.info(f"Generating pipeline from template: {args.pipeline_template_file}")
            generated_pipeline_file = pipeline_manager.generate_pipeline_from_template(
                template_file=args.pipeline_template_file,
                output_file=args.pipeline_file
            )
        else:
            logger.info(f"No template found ({args.pipeline_template_file}), using existing pipeline file: {args.pipeline_file}")
            generated_pipeline_file = args.pipeline_file
        
        # Prepare pipeline input overrides
        input_overrides = {}
        if args.input_data:
            input_overrides['input_data'] = args.input_data
        if args.storage_account:
            input_overrides['storage_account_name'] = args.storage_account
        if args.model_name:
            input_overrides['model_name'] = args.model_name
        if args.batch_size:
            input_overrides['batch_size'] = args.batch_size
        
        # Submit pipeline
        logger.info("Submitting pipeline job...")
        submitted_job = pipeline_manager.submit_pipeline(
            pipeline_file=generated_pipeline_file,
            **input_overrides
        )
        
        if args.no_monitor:
            logger.info("Pipeline submitted. Monitoring disabled.")
            logger.info(f"Monitor progress at: {submitted_job.studio_url}")
            return
        
        # Monitor job execution
        logger.info("Monitoring job execution...")
        completed_job = pipeline_manager.monitor_job(
            job=submitted_job,
            poll_interval=args.poll_interval
        )
        
        # Download outputs if requested
        if args.download_outputs and completed_job.status == "Completed":
            logger.info("Downloading job outputs...")
            pipeline_manager.download_outputs(completed_job)
        
        # Exit with appropriate code
        if completed_job.status == "Completed":
            logger.info("Pipeline execution completed successfully!")
            sys.exit(0)
        else:
            logger.error(f"Pipeline execution failed with status: {completed_job.status}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Pipeline execution failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
