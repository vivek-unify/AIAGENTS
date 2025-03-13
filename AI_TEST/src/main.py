# Updated main.py
import os
import sys
import yaml
import logging
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path
from crew import DevelopmentCrew
from openai_client import OpenAIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('project.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class ProjectManager:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.crew: Optional[DevelopmentCrew] = None
        self.project_config: Dict = {}
        self.openai_client: Optional[OpenAIClient] = None

    def load_configurations(self) -> bool:
        """Load all configuration files."""
        try:
            # Ensure config directory exists
            if not self.config_dir.exists():
                logger.error(f"Configuration directory {self.config_dir} not found")
                return False

            # Required configuration files
            required_files = [
                'agents.yaml',
                'tasks.yaml',
                'openai_config.yaml'
            ]

            # Check if all required files exist
            for file in required_files:
                if not (self.config_dir / file).exists():
                    logger.error(f"Required configuration file {file} not found")
                    return False

            # Check for OpenAI API key
            if not os.getenv('OPENAI_API_KEY'):
                logger.error("OPENAI_API_KEY environment variable not set")
                return False

            logger.info("All configurations and API key verified")
            return True

        except Exception as e:
            logger.error(f"Error loading configurations: {str(e)}")
            return False

    def initialize_project(self) -> bool:
        """Initialize the project and development crew."""
        try:
            if not self.load_configurations():
                return False

            # Initialize OpenAI client
            self.openai_client = OpenAIClient(str(self.config_dir / 'openai_config.yaml'))

            # Initialize the development crew
            self.crew = DevelopmentCrew(
                agents_config=str(self.config_dir / 'agents.yaml'),
                tasks_config=str(self.config_dir / 'tasks.yaml'),
                openai_client=self.openai_client
            )

            logger.info("Project initialized successfully with OpenAI integration")
            return True

        except Exception as e:
            logger.error(f"Error initializing project: {str(e)}")
            return False

    async def run_project(self) -> bool:
        """Execute the project workflow."""
        try:
            if not self.crew:
                logger.error("Development crew not initialized")
                return False

            start_time = datetime.now()
            logger.info(f"Starting project execution at {start_time}")

            # Execute the workflow
            await self.crew.execute_workflow()

            # Generate and save report
            end_time = datetime.now()
            execution_time = end_time - start_time
            
            report = self.crew.generate_report()
            report['execution_time'] = str(execution_time)
            
            # Save report
            report_path = Path('reports')
            report_path.mkdir(exist_ok=True)
            
            report_file = report_path / f'project_report_{end_time.strftime("%Y%m%d_%H%M%S")}.yaml'
            with open(report_file, 'w') as f:
                yaml.dump(report, f)

            logger.info(f"Project execution completed. Report saved to {report_file}")
            return True

        except Exception as e:
            logger.error(f"Error running project: {str(e)}")
            return False

async def main():
    """Main entry point of the application."""
    try:
        # Create project manager
        project_manager = ProjectManager()

        # Initialize project
        if not project_manager.initialize_project():
            logger.error("Failed to initialize project")
            sys.exit(1)

        # Run project
        if not await project_manager.run_project():
            logger.error("Failed to run project")
            sys.exit(1)

        logger.info("Project completed successfully")

    except Exception as e:
        logger.error(f"Unhandled error in main: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())