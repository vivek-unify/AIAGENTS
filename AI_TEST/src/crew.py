import yaml
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime
from openai_client import OpenAIClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    REVIEW = "Review"
    DONE = "Done"

@dataclass
class Task:
    task_id: str
    name: str
    description: str
    deliverables: List[str]
    dependencies: List[str]
    status: TaskStatus
    assigned_to: str
    created_at: datetime
    updated_at: datetime

class Agent:
    def __init__(self, role_config: Dict, openai_client: OpenAIClient):
        self.role_name = role_config['role_name']
        self.goal = role_config['goal']
        self.responsibilities = role_config.get('primary_responsibilities', [])
        self.current_task: Optional[Task] = None
        self.completed_tasks: List[Task] = []
        self.openai_client = openai_client

    def can_start_task(self, task: Task, completed_tasks: List[Task]) -> bool:
        if not task.dependencies:
            return True
        
        completed_task_ids = [t.task_id for t in completed_tasks]
        return all(dep in completed_task_ids for dep in task.dependencies)

    def assign_task(self, task: Task) -> bool:
        if self.current_task is not None:
            logger.warning(f"{self.role_name} already has an active task")
            return False
        
        self.current_task = task
        task.status = TaskStatus.IN_PROGRESS
        task.updated_at = datetime.now()
        task.assigned_to = self.role_name
        logger.info(f"Task {task.task_id} assigned to {self.role_name}")
        return True

    def complete_task(self) -> Optional[Task]:
        if self.current_task is None:
            logger.warning(f"{self.role_name} has no active task")
            return None
        
        self.current_task.status = TaskStatus.DONE
        self.current_task.updated_at = datetime.now()
        completed_task = self.current_task
        self.completed_tasks.append(completed_task)
        self.current_task = None
        logger.info(f"Task {completed_task.task_id} completed by {self.role_name}")
        return completed_task

    async def get_ai_response(self, prompt: str) -> str:
        """Get response from OpenAI API."""
        try:
            role = "architect" if isinstance(self, SoftwareArchitect) else "developer"
            return await self.openai_client.get_completion(role, prompt)
        except Exception as e:
            logger.error(f"Error getting AI response: {str(e)}")
            raise

class SoftwareArchitect(Agent):
    def __init__(self, config: Dict, openai_client: OpenAIClient):
        super().__init__(config['agents']['software_architect'], openai_client)
        self.design_patterns = config['agents']['software_architect']['core_competencies']['design_patterns']
        self.technical_skills = config['agents']['software_architect']['core_competencies']['technical_skills']
        self.authority_levels = config['agents']['software_architect']['authority_levels']

    async def review_implementation(self, task: Task) -> bool:
        if task.status != TaskStatus.REVIEW:
            logger.error(f"Task {task.task_id} is not ready for review")
            return False

        review_prompt = f"""
        Review the implementation of task:
        Task ID: {task.task_id}
        Name: {task.name}
        Description: {task.description}
        
        Verify that the implementation:
        1. Follows architectural guidelines
        2. Implements required design patterns
        3. Meets quality standards
        4. Adheres to best practices
        
        Provide a detailed review and approval decision.
        """

        review_response = await self.get_ai_response(review_prompt)
        logger.info(f"Architect review for task {task.task_id}: {review_response}")
        
        # Assume approval if no major issues raised in the response
        return "error" not in review_response.lower() and "reject" not in review_response.lower()

    async def provide_technical_guidance(self, task: Task) -> Dict:
        guidance_prompt = f"""
        As a Software Architect, provide technical guidance for the following task:
        Task: {task.description}
        
        Consider these design patterns: {self.design_patterns}
        Required technical skills: {self.technical_skills}
        
        Provide:
        1. Specific architectural guidelines
        2. Design patterns to implement
        3. Technical requirements
        4. Best practices to follow
        5. Implementation considerations
        """
        
        guidance_response = await self.get_ai_response(guidance_prompt)
        
        return {
            'design_patterns': [pattern for pattern in self.design_patterns 
                              if pattern.lower() in task.description.lower()],
            'technical_requirements': self.technical_skills,
            'implementation_guidelines': guidance_response
        }

class Developer(Agent):
    def __init__(self, config: Dict, openai_client: OpenAIClient):
        super().__init__(config['agents']['developer_agent'], openai_client)
        self.coding_practices = config['agents']['developer_agent']['coding_practices']
        self.technical_competencies = config['agents']['developer_agent']['required_skills']
        self.system_knowledge = config['agents']['developer_agent']['system_knowledge']

    async def implement_task(self, task: Task, guidance: Dict) -> bool:
        if self.current_task != task:
            logger.error(f"Task {task.task_id} is not assigned to this developer")
            return False

        implementation_prompt = f"""
        Implement the following task as a Developer:
        Task ID: {task.task_id}
        Name: {task.name}
        Description: {task.description}
        
        Technical Guidance:
        {guidance['implementation_guidelines']}
        
        Consider these coding practices:
        {self.coding_practices}
        
        Provide:
        1. Implementation approach
        2. Code structure
        3. Testing strategy
        4. Error handling
        5. Documentation requirements
        """
        
        implementation_response = await self.get_ai_response(implementation_prompt)
        logger.info(f"Implementation details for task {task.task_id}: {implementation_response}")
        
        task.status = TaskStatus.REVIEW
        task.updated_at = datetime.now()
        return True

class DevelopmentCrew:
    def __init__(self, agents_config: str, tasks_config: str, openai_client: OpenAIClient):
        # Load configurations
        with open(agents_config, 'r') as f:
            self.agents_config = yaml.safe_load(f)
        
        # Initialize agents with OpenAI client
        self.architect = SoftwareArchitect(self.agents_config, openai_client)
        self.developer = Developer(self.agents_config, openai_client)
        
        # Load tasks
        self.load_tasks(tasks_config)
        self.completed_tasks: List[Task] = []
        
        # Load interaction protocol
        self.interaction_protocol = self.agents_config.get('interaction_protocol', {})
        logger.info("Development crew initialized with interaction protocol")

    def load_tasks(self, tasks_config: str):
        with open(tasks_config, 'r') as f:
            tasks_data = yaml.safe_load(f)
        
        self.tasks = []
        for phase, phase_tasks in tasks_data['tasks'].items():
            for role_tasks in phase_tasks.values():
                for task_data in role_tasks:
                    self.tasks.append(
                        Task(
                            task_id=task_data['task_id'],
                            name=task_data['name'],
                            description=task_data['description'],
                            deliverables=task_data['deliverables'],
                            dependencies=task_data['dependencies'],
                            status=TaskStatus(task_data['status']),
                            assigned_to="",
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                    )

    def get_next_task(self) -> Optional[Task]:
        for task in self.tasks:
            if task.status == TaskStatus.TODO:
                if task.task_id.startswith('ARCH') and self.architect.can_start_task(task, self.completed_tasks):
                    return task
                elif task.task_id.startswith('DEV') and self.developer.can_start_task(task, self.completed_tasks):
                    return task
        return None

    async def execute_workflow(self):
        while True:
            next_task = self.get_next_task()
            if next_task is None:
                logger.info("All tasks completed!")
                break

            try:
                if next_task.task_id.startswith('ARCH'):
                    if self.architect.assign_task(next_task):
                        guidance = await self.architect.provide_technical_guidance(next_task)
                        completed_task = self.architect.complete_task()
                        if completed_task:
                            self.completed_tasks.append(completed_task)

                elif next_task.task_id.startswith('DEV'):
                    if self.developer.assign_task(next_task):
                        # Get guidance from architect
                        guidance = await self.architect.provide_technical_guidance(next_task)
                        # Implement task
                        if await self.developer.implement_task(next_task, guidance):
                            # Architect review
                            if await self.architect.review_implementation(next_task):
                                completed_task = self.developer.complete_task()
                                if completed_task:
                                    self.completed_tasks.append(completed_task)
                            else:
                                logger.warning(f"Task {next_task.task_id} failed architect review")
                                next_task.status = TaskStatus.TODO

            except Exception as e:
                logger.error(f"Error executing task {next_task.task_id}: {str(e)}")
                next_task.status = TaskStatus.TODO

    def generate_report(self) -> Dict:
        return {
            'total_tasks': len(self.tasks),
            'completed_tasks': len(self.completed_tasks),
            'architect_tasks': len([t for t in self.completed_tasks if t.task_id.startswith('ARCH')]),
            'developer_tasks': len([t for t in self.completed_tasks if t.task_id.startswith('DEV')]),
            'completion_time': (self.completed_tasks[-1].updated_at - self.completed_tasks[0].created_at
                              if self.completed_tasks else None),
            'task_details': [
                {
                    'task_id': task.task_id,
                    'name': task.name,
                    'status': task.status.value,
                    'assigned_to': task.assigned_to,
                    'completion_time': (task.updated_at - task.created_at).total_seconds()
                }
                for task in self.completed_tasks
            ]
        }