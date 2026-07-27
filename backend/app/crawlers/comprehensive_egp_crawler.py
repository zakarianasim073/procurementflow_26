"""
Comprehensive e-GP Crawler
Master crawler that coordinates all e-GP data collection activities
Crawls and imports everything from the e-GP system
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .egp_crawler import EGPCrawler
from .egp_document_crawler import EGPDocumentCrawler
from app.services.tender_manager import TenderManager
from app.services.intelligence_data_service_facade import IntelligenceDataServiceFacade
from app.db.database import get_session

logger = logging.getLogger(__name__)


class ComprehensiveEGPCrawler:
    """
    Master crawler that coordinates comprehensive e-GP data collection.
    
    This crawler:
    1. Crawls all live tenders from e-GP
    2. Crawls all archived tenders and opening reports
    3. Extracts all tender documents and specifications
    4. Collects all award and contract data
    5. Gathers experience data from eExperience
    6. Imports everything into PostgreSQL 17
    """

    def __init__(self, db=None):
        self.tender_crawler = EGPCrawler()
        self.document_crawler = EGPDocumentCrawler()
        self.tender_manager = TenderManager()
        self.db = db
        self._intelligence_service = None
        
        # Statistics tracking
        self.stats = {
            'tenders_crawled': 0,
            'awards_collected': 0,
            'documents_extracted': 0,
            'experience_records': 0,
            'contracts_imported': 0,
            'start_time': datetime.now(timezone.utc),
            'end_time': None
        }

    async def _get_intelligence_service(self):
        """Lazy-load intelligence service with a DB session."""
        if self._intelligence_service is None:
            if self.db is None:
                async with get_session() as session:
                    self._intelligence_service = IntelligenceDataServiceFacade(session)
            else:
                self._intelligence_service = IntelligenceDataServiceFacade(self.db)
        return self._intelligence_service

    async def crawl_everything(self, years_back: int = 5, concurrency: int = 3) -> Dict[str, Any]:
        """
        Comprehensive crawl of all e-GP data
        
        Args:
            years_back: Number of years of historical data to collect
            concurrency: Number of concurrent crawlers to run
        """
        self.stats['start_time'] = datetime.now(timezone.utc)
        logger.info("🚀 Starting comprehensive e-GP crawl")
        logger.info(f"📅 Collecting {years_back} years of historical data")
        logger.info(f"🔄 Using {concurrency} concurrent crawlers")
        
        try:
            # Phase 1: Crawl all live tenders
            await self._crawl_live_tenders()
            
            # Phase 2: Crawl archived tenders and opening reports
            await self._crawl_archived_tenders(years_back)
            
            # Phase 3: Extract tender documents
            await self._extract_tender_documents(concurrency)
            
            # Phase 4: Collect award and contract data
            await self._collect_awards_and_contracts()
            
            # Phase 5: Gather experience data
            await self._gather_experience_data()
            
            # Phase 6: Import all data into database
            await self._import_all_data()
            
            self.stats['end_time'] = datetime.now(timezone.utc)
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            
            logger.info("✅ Comprehensive e-GP crawl completed successfully!")
            logger.info(f"⏱️  Duration: {duration:.1f} seconds")
            logger.info(f"📊 Summary: {self.stats}")
            
            return {
                'status': 'success',
                'stats': self.stats,
                'duration_seconds': duration,
                'message': 'Comprehensive e-GP data collection completed'
            }
            
        except Exception as e:
            logger.error(f"❌ Comprehensive crawl failed: {e}", exc_info=True)
            return {
                'status': 'failed',
                'error': str(e),
                'stats': self.stats
            }

    async def _crawl_live_tenders(self) -> None:
        """Crawl all live tenders from e-GP"""
        logger.info("🔍 Phase 1/6: Crawling live tenders...")
        
        try:
            # Use the existing tender crawler to get live tenders
            live_tenders = await self.tender_crawler.crawl_live_tenders()
            
            for tender in live_tenders:
                # Process and store each tender
                await self.tender_manager.process_tender_data(tender)
                self.stats['tenders_crawled'] += 1
                
                if self.stats['tenders_crawled'] % 10 == 0:
                    logger.info(f"📊 Crawled {self.stats['tenders_crawled']} live tenders...")
            
            logger.info(f"✅ Completed live tender crawl: {self.stats['tenders_crawled']} tenders")
            
        except Exception as e:
            logger.error(f"❌ Live tender crawl failed: {e}")
            raise

    async def _crawl_archived_tenders(self, years_back: int) -> None:
        """Crawl archived tenders and opening reports"""
        logger.info(f"🔍 Phase 2/6: Crawling archived tenders (last {years_back} years)...")
        
        try:
            # Calculate date range
            end_date = datetime.now().date()
            start_date = end_date.replace(year=end_date.year - years_back)
            
            # Crawl archived tenders year by year
            current_year = start_date.year
            while current_year <= end_date.year:
                logger.info(f"📅 Crawling archived tenders for {current_year}...")
                
                # Get archived tenders for this year
                archived_tenders = await self.tender_crawler.crawl_archived_tenders(current_year)
                
                for tender in archived_tenders:
                    # Process archived tender
                    await self.tender_manager.process_tender_data(tender, is_archived=True)
                    self.stats['tenders_crawled'] += 1
                    
                    # Also get opening report if available
                    opening_report = await self.tender_crawler.crawl_opening_report(tender['tender_id'])
                    if opening_report:
                        await self._get_intelligence_service()
                        await self._intelligence_service.store_opening_report(opening_report)
                        self.stats['awards_collected'] += 1
                
                logger.info(f"✅ Completed {current_year}: {len(archived_tenders)} tenders, {self.stats['awards_collected']} awards")
                current_year += 1
            
            logger.info(f"✅ Completed archived tender crawl: {self.stats['tenders_crawled']} total tenders")
            
        except Exception as e:
            logger.error(f"❌ Archived tender crawl failed: {e}")
            raise

    async def _extract_tender_documents(self, concurrency: int) -> None:
        """Extract documents from all crawled tenders using parallel processing"""
        logger.info(f"🔍 Phase 3/6: Extracting tender documents ({concurrency} concurrent crawlers)...")
        
        try:
            # Get all tenders that need document extraction
            tenders_needing_docs = await self.tender_manager.get_tenders_needing_documents()
            total_tenders = len(tenders_needing_docs)
            
            if total_tenders == 0:
                logger.info("ℹ️  No tenders need document extraction")
                return
                
            logger.info(f"📚 Processing {total_tenders} tenders for document extraction...")
            
            # Process tenders in batches with concurrency
            semaphore = asyncio.Semaphore(concurrency)
            
            async def process_tender(tender):
                async with semaphore:
                    try:
                        # Extract documents for this tender
                        docs = await self.document_crawler.extract_tender_documents(tender['tender_id'])
                        
                        if docs:
                            await self.tender_manager.store_tender_documents(tender['tender_id'], docs)
                            self.stats['documents_extracted'] += 1
                            
                            if self.stats['documents_extracted'] % 10 == 0:
                                logger.info(f"📄 Extracted documents from {self.stats['documents_extracted']}/{total_tenders} tenders...")
                                
                    except Exception as e:
                        logger.error(f"❌ Failed to extract documents for tender {tender['tender_id']}: {e}")
            
            # Run all tenders through the semaphore
            tasks = [process_tender(tender) for tender in tenders_needing_docs]
            await asyncio.gather(*tasks)
            
            logger.info(f"✅ Completed document extraction: {self.stats['documents_extracted']} tenders processed")
            
        except Exception as e:
            logger.error(f"❌ Document extraction failed: {e}")
            raise

    async def _collect_awards_and_contracts(self) -> None:
        """Collect comprehensive award and contract data"""
        logger.info("🔍 Phase 4/6: Collecting awards and contracts data...")
        
        try:
            # Use the intelligence service to collect award data
            awards_data = await self._get_intelligence_service()
            awards_data = await self._intelligence_service.collect_comprehensive_awards_data()
            
            for award in awards_data:
                await self._intelligence_service.store_award_record(award)
                self.stats['awards_collected'] += 1
                
                # Extract contract information from award
                contract = self._extract_contract_from_award(award)
                if contract:
                    await self._intelligence_service.store_contract_record(contract)
                    self.stats['contracts_imported'] += 1
            
            logger.info(f"✅ Completed awards/contracts collection: {self.stats['awards_collected']} awards, {self.stats['contracts_imported']} contracts")
            
        except Exception as e:
            logger.error(f"❌ Awards/contracts collection failed: {e}")
            raise

    def _extract_contract_from_award(self, award: Dict) -> Optional[Dict]:
        """Extract contract information from an award record"""
        if not award.get('contract_no') and not award.get('contract_date'):
            return None
            
        return {
            'contract_id': award.get('contract_no', f"CONTRACT-{award['tender_id']}"),
            'tender_id': award['tender_id'],
            'package_no': award.get('package_no', ''),
            'agency_code': award.get('agency_code', ''),
            'contractor_name': award.get('contractor_name', ''),
            'contract_value': award.get('amount_bdt', 0),
            'contract_date': award.get('contract_date', ''),
            'completion_date': award.get('completion_date', ''),
            'status': award.get('status', 'awarded'),
            'source': 'eGP award data'
        }

    async def _gather_experience_data(self) -> None:
        """Gather contractor experience data from eExperience"""
        logger.info("🔍 Phase 5/6: Gathering experience data...")
        
        try:
            # Collect experience data for all contractors found in awards
            svc = await self._get_intelligence_service()
            contractors = await svc.get_all_contractors_from_awards()
            
            for contractor in contractors:
                # Get experience data for this contractor
                experience_data = await svc.collect_contractor_experience(contractor)
                
                if experience_data:
                    for exp_record in experience_data:
                        await svc.store_experience_record(exp_record)
                        self.stats['experience_records'] += 1
                
                if self.stats['experience_records'] % 5 == 0:
                    logger.info(f"📋 Collected experience data for {self.stats['experience_records']} contractor records...")
            
            logger.info(f"✅ Completed experience data collection: {self.stats['experience_records']} records")
            
        except Exception as e:
            logger.error(f"❌ Experience data collection failed: {e}")
            raise

    async def _import_all_data(self) -> None:
        """Final import of all collected data into PostgreSQL 17"""
        logger.info("🔍 Phase 6/6: Final data import to PostgreSQL 17...")
        
        try:
            # Import all tenders
            tender_import = await self.tender_manager.import_all_tenders_to_database()
            logger.info(f"📥 Imported {tender_import['imported']} tenders to database")
            
            # Import all awards
            svc = await self._get_intelligence_service()
            award_import = await svc.import_all_awards_to_database()
            logger.info(f"📥 Imported {award_import['imported']} awards to database")
            
            # Import all contracts
            contract_import = await svc.import_all_contracts_to_database()
            logger.info(f"📥 Imported {contract_import['imported']} contracts to database")
            
            # Import all experience records
            exp_import = await svc.import_all_experience_to_database()
            logger.info(f"📥 Imported {exp_import['imported']} experience records to database")
            
            # Generate contractor DNA profiles
            dna_result = await svc.generate_contractor_dna_profiles()
            logger.info(f"🧬 Generated {dna_result['generated']} contractor DNA profiles")
            
            logger.info("✅ Completed final data import to PostgreSQL 17")
            
        except Exception as e:
            logger.error(f"❌ Final data import failed: {e}")
            raise

    async def get_progress(self) -> Dict[str, Any]:
        """Get current progress of the comprehensive crawl"""
        duration = (datetime.now(timezone.utc) - self.stats['start_time']).total_seconds() if self.stats['start_time'] else 0
        
        return {
            'status': 'running' if not self.stats['end_time'] else 'completed',
            'stats': self.stats,
            'duration_seconds': duration,
            'estimated_completion': None  # Could add estimation logic
        }

    async def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed statistics about the crawl"""
        # Get database counts
        db_stats = await self._get_database_counts()
        
        return {
            **self.stats,
            'database': db_stats,
            'crawl_efficiency': self._calculate_efficiency()
        }

    async def _get_database_counts(self) -> Dict[str, int]:
        """Get current record counts from the database"""
        try:
            from app.db.database import get_session
            
            async with get_session() as session:
                # Get counts from key tables
                result = await session.execute("SELECT COUNT(*) FROM tenders")
                tenders_count = result.scalar()
                
                result = await session.execute("SELECT COUNT(*) FROM award_records")
                awards_count = result.scalar()
                
                result = await session.execute("SELECT COUNT(*) FROM contracts")
                contracts_count = result.scalar()
                
                result = await session.execute("SELECT COUNT(*) FROM econtract_execution")
                experience_count = result.scalar()
                
                result = await session.execute("SELECT COUNT(*) FROM contractor_dna")
                dna_count = result.scalar()
                
                return {
                    'tenders': tenders_count,
                    'awards': awards_count,
                    'contracts': contracts_count,
                    'experience': experience_count,
                    'contractor_dna': dna_count
                }
        except Exception as e:
            logger.error(f"❌ Could not get database counts: {e}")
            return {
                'tenders': 0,
                'awards': 0,
                'contracts': 0,
                'experience': 0,
                'contractor_dna': 0
            }

    def _calculate_efficiency(self) -> Dict[str, float]:
        """Calculate crawl efficiency metrics"""
        if not self.stats['start_time'] or not self.stats['end_time']:
            return {'tenders_per_minute': 0, 'overall_score': 0}
            
        duration_minutes = (self.stats['end_time'] - self.stats['start_time']).total_seconds() / 60
        
        if duration_minutes > 0:
            tenders_per_minute = self.stats['tenders_crawled'] / duration_minutes
        else:
            tenders_per_minute = 0
            
        # Simple efficiency score (0-100)
        efficiency_score = min(100, tenders_per_minute * 2)  # Cap at 100
        
        return {
            'tenders_per_minute': round(tenders_per_minute, 2),
            'overall_score': round(efficiency_score, 1)
        }