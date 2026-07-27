"""
Focused Awards Orchestrator
Specialized orchestrator for collecting awards, experience, and contracts data
from all PE offices under all ministries using multiple agents
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.agents.core.base import BaseAgent, AgentResult, AgentStatus
from .registry import AgentRegistry
from .multi_agent_awards_config import (
    MultiAgentPhase,
    FOCUSED_PIPELINE_DEFINITION,
    MULTI_AGENT_CONFIG,
    AGENT_SPECIFIC_CONFIGS,
    DB_VERIFICATION_QUERIES,
    TARGET_MINISTRIES,
    DEPARTMENT_IDS
)

logger = logging.getLogger(__name__)


class FocusedAwardsOrchestrator(BaseAgent):
    """
    Specialized orchestrator for awards, experience, and contracts data collection.
    
    Skips APP data crawling and focuses exclusively on:
    - Historical award data from eGP
    - Contract experience data from eExperience
    - Contractor performance data
    - Competitor intelligence
    """

    agent_id = "agent-focused-awards-orchestrator"
    agent_name = "Focused Awards Orchestrator"
    description = "Orchestrates multiple agents to collect awards, experience, and contracts data from all PE offices under all ministries."
    dependencies: List[str] = []
    version = "1.0.0"

    def __init__(self, brain=None) -> None:
        super().__init__(brain=brain)
        self._registry = AgentRegistry()
        self._run_id: str = ""
        self._phase_results: Dict[str, Any] = {}
        self._collected_data: Dict[str, List[Dict]] = {
            "awards": [],
            "contracts": [],
            "experience": [],
            "contractor_profiles": [],
        }

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """
        Execute the focused data collection pipeline.
        
        Context options:
        - ministries: List of ministries to target (default: all)
        - agencies: List of specific agencies to target (default: all)
        - years_back: Number of years of historical data (default: 5)
        - concurrency: Number of concurrent agents (default: 5)
        """
        self._run_id = f"awards-run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        
        # Merge context with default config
        config = {**MULTI_AGENT_CONFIG, **context}
        
        logger.info(f"[FocusedAwardsOrchestrator] Starting run {self._run_id}")
        logger.info(f"[FocusedAwardsOrchestrator] Targeting {len(DEPARTMENT_IDS)} agencies across {len(TARGET_MINISTRIES)} ministries")
        
        try:
            # Initialize database connection
            await self._initialize_database()
            
            # Run the focused pipeline
            result = await self._run_focused_pipeline(config)
            
            # Verify data import
            verification = await self._verify_database_population()
            
            output = {
                "run_id": self._run_id,
                "status": "Focused awards data collection completed",
                "phases": result,
                "data_summary": {
                    "awards_collected": len(self._collected_data["awards"]),
                    "contracts_collected": len(self._collected_data["contracts"]),
                    "experience_records": len(self._collected_data["experience"]),
                    "contractor_profiles": len(self._collected_data["contractor_profiles"]),
                },
                "database_verification": verification,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            return AgentResult(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                status=AgentStatus.SUCCESS,
                output=output,
            )

        except Exception as exc:
            logger.error(f"[FocusedAwardsOrchestrator] Run failed: {exc}")
            return AgentResult(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                status=AgentStatus.FAILED,
                output={"run_id": self._run_id, "error": str(exc)},
            )

    async def _initialize_database(self) -> None:
        """Initialize database connections and prepare for data import"""
        from app.db.database import get_session
        from app.models.intelligence import AwardRecordV2, EContractExecution, ContractorDNA
        
        logger.info("[FocusedAwardsOrchestrator] Initializing database connection")
        
        # Clear any existing data if this is a fresh run
        # Note: In production, you might want to comment this out
        async with get_session() as session:
            # Check if tables are empty or if we should append
            award_count = await session.execute("SELECT COUNT(*) FROM award_records")
            award_count = award_count.scalar()
            
            if award_count > 10000:  # If we already have significant data
                logger.warning(f"[FocusedAwardsOrchestrator] Found {award_count} existing award records - will append")
            else:
                logger.info(f"[FocusedAwardsOrchestrator] Starting with clean database ({award_count} existing records)")

    async def _run_focused_pipeline(self, config: Dict) -> Dict:
        """Run the focused data collection pipeline"""
        all_results: Dict[str, Any] = {}
        
        # Get phases in order
        phases = list(MultiAgentPhase)
        total_phases = len(phases)
        
        for idx, phase in enumerate(phases, 1):
            logger.info(f"[FocusedAwardsOrchestrator] Phase {idx}/{total_phases}: {phase.value}")
            
            if phase == MultiAgentPhase.AWARDS_COLLECTION:
                phase_result = await self._run_awards_collection_phase(config)
            elif phase == MultiAgentPhase.EXPERIENCE_COLLECTION:
                phase_result = await self._run_experience_collection_phase(config)
            elif phase == MultiAgentPhase.CONTRACTS_COLLECTION:
                phase_result = await self._run_contracts_collection_phase(config)
            elif phase == MultiAgentPhase.DATA_RECONCILIATION:
                phase_result = await self._run_data_reconciliation_phase(config)
            elif phase == MultiAgentPhase.ANALYSIS:
                phase_result = await self._run_analysis_phase(config)
            else:
                phase_result = {"status": "skipped", "reason": "phase not implemented"}
                
            all_results[phase.value] = phase_result
            
        return all_results

    async def _run_awards_collection_phase(self, config: Dict) -> Dict:
        """Run the awards collection phase using multiple agents"""
        agent_ids = FOCUSED_PIPELINE_DEFINITION[MultiAgentPhase.AWARDS_COLLECTION]
        
        # Configure agents with ministry/agency targets
        agent_contexts = []
        for agent_id in agent_ids:
            agent_config = AGENT_SPECIFIC_CONFIGS.get(agent_id, {})
            context = {
                **config,
                **agent_config,
                "target_ministries": TARGET_MINISTRIES,
                "department_ids": DEPARTMENT_IDS,
                "focus": "awards_collection",
            }
            agent_contexts.append((agent_id, context))
        
        # Run agents with concurrency
        results = await self._run_agents_concurrently(agent_contexts, config["concurrency"])
        
        # Collect and aggregate results
        awards_collected = 0
        for agent_id, result in results.items():
            if result.status == AgentStatus.SUCCESS:
                agent_data = result.output.get("data", [])
                if agent_data:
                    self._collected_data["awards"].extend(agent_data)
                    awards_collected += len(agent_data)
        
        return {
            "agents_run": len(agent_ids),
            "awards_collected": awards_collected,
            "agent_results": results,
        }

    async def _run_experience_collection_phase(self, config: Dict) -> Dict:
        """Run the experience data collection phase"""
        # Experience data is primarily collected through services
        from app.services.experience_reconciliation_service import ExperienceReconciliationService
        
        service = ExperienceReconciliationService()
        
        # Process collected awards data to extract experience information
        experience_data = []
        for award in self._collected_data["awards"]:
            exp_record = {
                "package_no": award.get("package_no", ""),
                "contractor_name": award.get("contractor_name", ""),
                "contract_value": award.get("amount_bdt", 0),
                "start_date": award.get("contract_date", ""),
                "completion_date": award.get("completion_date", ""),
                "status": "completed" if award.get("status") == "Awarded" else "ongoing",
            }
            experience_data.append(exp_record)
        
        # Import experience data
        import_result = await service.import_eexperience_from_json(experience_data)
        
        self._collected_data["experience"].extend(experience_data)
        
        return {
            "experience_records_imported": import_result.get("imported", 0),
            "total_experience_records": len(experience_data),
        }

    async def _run_contracts_collection_phase(self, config: Dict) -> Dict:
        """Run the contracts data collection phase"""
        # Contracts data is derived from awards and experience data
        contracts_data = []
        
        for award in self._collected_data["awards"]:
            contract_record = {
                "contract_id": f"CONTRACT-{award.get('package_no', '')}",
                "package_no": award.get("package_no", ""),
                "agency_code": award.get("agency_code", ""),
                "contractor_name": award.get("contractor_name", ""),
                "contract_value": award.get("amount_bdt", 0),
                "contract_date": award.get("contract_date", ""),
                "completion_date": award.get("completion_date", ""),
                "status": award.get("status", ""),
            }
            contracts_data.append(contract_record)
        
        self._collected_data["contracts"].extend(contracts_data)
        
        return {
            "contracts_collected": len(contracts_data),
        }

    async def _run_data_reconciliation_phase(self, config: Dict) -> Dict:
        """Run data reconciliation and contractor DNA generation"""
        from app.services.contractor_dna_service import ContractorDNAService
        
        dna_service = ContractorDNAService()
        
        # Generate contractor DNA profiles from collected data
        contractor_profiles = {}
        for record in self._collected_data["awards"]:
            contractor_name = record.get("contractor_name", "")
            if not contractor_name:
                continue
                
            if contractor_name not in contractor_profiles:
                contractor_profiles[contractor_name] = {
                    "name": contractor_name,
                    "awards_count": 0,
                    "total_value": 0,
                    "agencies_worked_with": set(),
                    "work_types": set(),
                }
            
            profile = contractor_profiles[contractor_name]
            profile["awards_count"] += 1
            profile["total_value"] += record.get("amount_bdt", 0)
            profile["agencies_worked_with"].add(record.get("agency_code", ""))
            profile["work_types"].add(record.get("work_type", ""))
        
        # Generate DNA vectors and store profiles
        dna_results = []
        for contractor_name, profile in contractor_profiles.items():
            dna_vector = await dna_service.generate_dna_vector(
                contractor_name,
                profile["awards_count"],
                profile["total_value"],
                list(profile["agencies_worked_with"]),
                list(profile["work_types"])
            )
            
            profile["dna_vector"] = dna_vector
            self._collected_data["contractor_profiles"].append(profile)
            dna_results.append({
                "contractor": contractor_name,
                "dna_vector": dna_vector,
                "awards_count": profile["awards_count"],
            })
        
        return {
            "contractor_profiles_generated": len(contractor_profiles),
            "dna_vectors_generated": len(dna_results),
            "dna_samples": dna_results[:5],  # Show first 5 as examples
        }

    async def _run_analysis_phase(self, config: Dict) -> Dict:
        """Run analysis on collected data"""
        # Run competitor analysis
        competitor_results = await self._run_agents_concurrently(
            [("agent-015-competitor-pricing-predictor", {
                "awards_data": self._collected_data["awards"],
                "contractor_profiles": self._collected_data["contractor_profiles"],
            })],
            concurrency=1
        )
        
        # Run win probability analysis
        win_prob_results = await self._run_agents_concurrently(
            [("agent-016-win-probability", {
                "historical_awards": self._collected_data["awards"],
                "contractor_profiles": self._collected_data["contractor_profiles"],
            })],
            concurrency=1
        )
        
        return {
            "competitor_analysis": competitor_results,
            "win_probability_analysis": win_prob_results,
            "data_summary": {
                "total_awards": len(self._collected_data["awards"]),
                "total_contracts": len(self._collected_data["contracts"]),
                "total_experience": len(self._collected_data["experience"]),
                "total_contractors": len(self._collected_data["contractor_profiles"]),
            }
        }

    async def _run_agents_concurrently(self, agent_contexts: List, concurrency: int) -> Dict:
        """Run multiple agents concurrently with rate limiting"""
        semaphore = asyncio.Semaphore(concurrency)
        results = {}
        
        async def run_agent(agent_id: str, context: Dict):
            async with semaphore:
                try:
                    agent = await self._registry.get_agent(agent_id)
                    if agent:
                        result = await agent.execute(context)
                        return (agent_id, result)
                    else:
                        return (agent_id, AgentResult(
                            agent_id=agent_id,
                            agent_name=agent_id,
                            status=AgentStatus.FAILED,
                            output={"error": "Agent not found"}
                        ))
                except Exception as e:
                    return (agent_id, AgentResult(
                        agent_id=agent_id,
                        agent_name=agent_id,
                        status=AgentStatus.FAILED,
                        output={"error": str(e)}
                    ))
        
        tasks = [run_agent(agent_id, context) for agent_id, context in agent_contexts]
        completed = await asyncio.gather(*tasks)
        
        for agent_id, result in completed:
            results[agent_id] = result
            
            if result.status == AgentStatus.SUCCESS:
                logger.info(f"[FocusedAwardsOrchestrator] Agent {agent_id} completed successfully")
            else:
                logger.warning(f"[FocusedAwardsOrchestrator] Agent {agent_id} failed: {result.output.get('error', 'unknown error')}")
        
        return results

    async def _verify_database_population(self) -> Dict:
        """Verify that data has been properly imported into the database"""
        from app.db.database import get_session
        
        verification_results = {}
        
        async with get_session() as session:
            for query_name, query in DB_VERIFICATION_QUERIES.items():
                try:
                    result = await session.execute(query)
                    
                    if query_name.endswith("_count"):
                        count = result.scalar()
                        verification_results[query_name] = count
                    elif query_name == "recent_awards":
                        records = result.fetchall()
                        verification_results[query_name] = [dict(r) for r in records]
                    elif query_name == "data_quality_check":
                        record = result.fetchone()
                        if record:
                            verification_results[query_name] = {
                                "missing_contract_values": record[0],
                                "missing_contractor_names": record[1],
                                "missing_package_nos": record[2],
                                "total_records": record[3],
                                "data_completeness": {
                                    "contract_values": max(0, 100 - (record[0] / record[3] * 100)) if record[3] > 0 else 0,
                                    "contractor_names": max(0, 100 - (record[1] / record[3] * 100)) if record[3] > 0 else 0,
                                    "package_nos": max(0, 100 - (record[2] / record[3] * 100)) if record[3] > 0 else 0,
                                }
                            }
                    
                except Exception as e:
                    verification_results[query_name] = {"error": str(e)}
        
        # Calculate overall data quality score
        quality_check = verification_results.get("data_quality_check", {})
        if isinstance(quality_check, dict) and "data_completeness" in quality_check:
            completeness = quality_check["data_completeness"]
            overall_quality = sum(completeness.values()) / len(completeness)
            verification_results["overall_data_quality"] = round(overall_quality, 2)
        
        return verification_results

    async def get_progress(self) -> Dict:
        """Get current progress of the data collection"""
        return {
            "run_id": self._run_id,
            "data_collected": {
                "awards": len(self._collected_data["awards"]),
                "contracts": len(self._collected_data["contracts"]),
                "experience": len(self._collected_data["experience"]),
                "contractor_profiles": len(self._collected_data["contractor_profiles"]),
            },
            "status": "running" if self._run_id else "not_started",
        }
