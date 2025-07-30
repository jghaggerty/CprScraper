import asyncio
import hashlib
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import aiohttp
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from ..database.connection import get_db
from ..database.models import Agency, Form, FormChange, MonitoringRun
from ..utils.config_loader import load_agency_config

logger = logging.getLogger(__name__)


class WebScraper:
    """Core web scraping class for monitoring government websites."""
    
    def __init__(self, user_agent: str = None, timeout: int = 30):
        self.user_agent = user_agent or "PayrollMonitor/1.0 (Government Forms Monitoring)"
        self.timeout = timeout
        self.session = None
        self.driver = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={"User-Agent": self.user_agent}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
        if self.driver:
            self.driver.quit()
    
    def _setup_selenium_driver(self) -> webdriver.Chrome:
        """Set up Selenium Chrome driver for JavaScript-heavy sites."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument(f"--user-agent={self.user_agent}")
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(self.timeout)
            return driver
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            return None
    
    async def fetch_page_content(self, url: str, use_selenium: bool = False) -> Tuple[str, int, Dict]:
        """
        Fetch page content using either aiohttp or Selenium.
        
        Returns:
            Tuple of (content, status_code, metadata)
        """
        metadata = {
            "url": url,
            "timestamp": datetime.utcnow().isoformat(),
            "method": "selenium" if use_selenium else "aiohttp"
        }
        
        if use_selenium:
            return await self._fetch_with_selenium(url, metadata)
        else:
            return await self._fetch_with_aiohttp(url, metadata)
    
    async def _fetch_with_aiohttp(self, url: str, metadata: Dict) -> Tuple[str, int, Dict]:
        """Fetch content using aiohttp."""
        try:
            async with self.session.get(url) as response:
                content = await response.text()
                metadata.update({
                    "status_code": response.status,
                    "content_type": response.headers.get("content-type", ""),
                    "content_length": len(content),
                    "last_modified": response.headers.get("last-modified", "")
                })
                return content, response.status, metadata
        except Exception as e:
            logger.error(f"Error fetching {url} with aiohttp: {e}")
            metadata["error"] = str(e)
            return "", 0, metadata
    
    async def _fetch_with_selenium(self, url: str, metadata: Dict) -> Tuple[str, int, Dict]:
        """Fetch content using Selenium for JavaScript-heavy sites."""
        if not self.driver:
            self.driver = self._setup_selenium_driver()
        
        if not self.driver:
            metadata["error"] = "Failed to initialize Selenium driver"
            return "", 0, metadata
        
        try:
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            content = self.driver.page_source
            metadata.update({
                "status_code": 200,
                "content_length": len(content),
                "current_url": self.driver.current_url
            })
            
            return content, 200, metadata
            
        except TimeoutException:
            logger.error(f"Timeout loading {url} with Selenium")
            metadata["error"] = "Timeout"
            return "", 408, metadata
        except WebDriverException as e:
            logger.error(f"Selenium error for {url}: {e}")
            metadata["error"] = str(e)
            return "", 0, metadata
    
    def extract_form_links(self, content: str, base_url: str) -> List[Dict]:
        """Extract form/document links from page content."""
        soup = BeautifulSoup(content, 'html.parser')
        form_links = []
        
        # Common selectors for form links
        selectors = [
            'a[href*=".pdf"]',
            'a[href*="form"]',
            'a[href*="report"]',
            'a[href*="payroll"]',
            'a[href*="prevailing"]',
            'a[href*="wage"]',
            'a[download]'
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    absolute_url = urljoin(base_url, href)
                    form_links.append({
                        'url': absolute_url,
                        'text': link.get_text(strip=True),
                        'title': link.get('title', ''),
                        'download': link.get('download', ''),
                        'selector': selector
                    })
        
        return form_links
    
    def calculate_content_hash(self, content: str) -> str:
        """Calculate SHA256 hash of content for change detection."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def detect_changes(self, old_content: str, new_content: str) -> List[Dict]:
        """Detect changes between old and new content."""
        changes = []
        
        old_hash = self.calculate_content_hash(old_content)
        new_hash = self.calculate_content_hash(new_content)
        
        if old_hash != new_hash:
            # Basic change detection - in production, you'd want more sophisticated diff
            old_soup = BeautifulSoup(old_content, 'html.parser')
            new_soup = BeautifulSoup(new_content, 'html.parser')
            
            # Check for new forms
            old_links = self.extract_form_links(old_content, "")
            new_links = self.extract_form_links(new_content, "")
            
            old_urls = {link['url'] for link in old_links}
            new_urls = {link['url'] for link in new_links}
            
            added_links = new_urls - old_urls
            removed_links = old_urls - new_urls
            
            if added_links:
                changes.append({
                    'type': 'new_forms',
                    'description': f"New forms detected: {len(added_links)} new links",
                    'details': list(added_links)
                })
            
            if removed_links:
                changes.append({
                    'type': 'removed_forms',
                    'description': f"Forms removed: {len(removed_links)} links no longer available",
                    'details': list(removed_links)
                })
            
            # Check for content changes
            old_text = old_soup.get_text()
            new_text = new_soup.get_text()
            
            if old_text != new_text:
                changes.append({
                    'type': 'content_change',
                    'description': "Page content has been modified",
                    'old_hash': old_hash,
                    'new_hash': new_hash
                })
        
        return changes


class AgencyMonitor:
    """High-level monitor for government agencies."""
    
    def __init__(self):
        self.scraper = None
        
    async def monitor_agency(self, agency_id: int) -> List[Dict]:
        """Monitor a specific agency for changes."""
        changes_detected = []
        
        with get_db() as db:
            agency = db.query(Agency).filter(Agency.id == agency_id).first()
            if not agency:
                logger.error(f"Agency {agency_id} not found")
                return changes_detected
            
            logger.info(f"Monitoring agency: {agency.name}")
            
            # Start monitoring run
            run = MonitoringRun(
                agency_id=agency_id,
                status="running"
            )
            db.add(run)
            db.commit()
            
            try:
                async with WebScraper() as scraper:
                    self.scraper = scraper
                    
                    # Monitor each form for this agency
                    for form in agency.forms:
                        if not form.is_active:
                            continue
                            
                        form_changes = await self._monitor_form(form, db)
                        changes_detected.extend(form_changes)
                        
                        # Update form's last checked time
                        form.last_checked = datetime.utcnow()
                        db.commit()
                
                # Update monitoring run
                run.completed_at = datetime.utcnow()
                run.status = "completed"
                run.changes_detected = len(changes_detected)
                db.commit()
                
            except Exception as e:
                logger.error(f"Error monitoring agency {agency.name}: {e}")
                run.status = "failed"
                run.error_message = str(e)
                db.commit()
        
        return changes_detected
    
    async def _monitor_form(self, form: Form, db) -> List[Dict]:
        """Monitor a specific form for changes."""
        changes = []
        
        try:
            # Fetch current content
            content, status_code, metadata = await self.scraper.fetch_page_content(
                form.form_url or form.agency.base_url
            )
            
            if status_code != 200:
                logger.warning(f"Failed to fetch {form.name}: HTTP {status_code}")
                return changes
            
            # Calculate content hash
            content_hash = self.scraper.calculate_content_hash(content)
            
            # Get the last monitoring run for this form
            last_run = db.query(MonitoringRun).filter(
                MonitoringRun.form_id == form.id
            ).order_by(MonitoringRun.started_at.desc()).first()
            
            if last_run and last_run.content_hash:
                # Compare with previous content
                if last_run.content_hash != content_hash:
                    # Content has changed - fetch previous content for detailed comparison
                    # For now, we'll create a basic change record
                    change = FormChange(
                        form_id=form.id,
                        change_type="content",
                        change_description="Form content has been modified",
                        new_value=content_hash,
                        old_value=last_run.content_hash,
                        change_hash=content_hash
                    )
                    db.add(change)
                    changes.append({
                        'form_id': form.id,
                        'form_name': form.name,
                        'change_type': 'content',
                        'description': 'Form content has been modified'
                    })
            
            # Create new monitoring run for this form
            form_run = MonitoringRun(
                agency_id=form.agency_id,
                form_id=form.id,
                status="completed",
                completed_at=datetime.utcnow(),
                content_hash=content_hash,
                http_status_code=status_code
            )
            db.add(form_run)
            
        except Exception as e:
            logger.error(f"Error monitoring form {form.name}: {e}")
            
            # Create failed monitoring run
            form_run = MonitoringRun(
                agency_id=form.agency_id,
                form_id=form.id,
                status="failed",
                completed_at=datetime.utcnow(),
                error_message=str(e),
                http_status_code=0
            )
            db.add(form_run)
        
        return changes
    
    async def monitor_all_agencies(self) -> Dict[str, List]:
        """Monitor all active agencies."""
        results = {}
        
        with get_db() as db:
            agencies = db.query(Agency).filter(Agency.is_active == True).all()
            
            for agency in agencies:
                try:
                    changes = await self.monitor_agency(agency.id)
                    results[agency.name] = changes
                    logger.info(f"Completed monitoring {agency.name}: {len(changes)} changes detected")
                except Exception as e:
                    logger.error(f"Failed to monitor {agency.name}: {e}")
                    results[agency.name] = []
        
        return results


async def main():
    """Main function for testing the monitor."""
    monitor = AgencyMonitor()
    results = await monitor.monitor_all_agencies()
    
    for agency_name, changes in results.items():
        print(f"{agency_name}: {len(changes)} changes detected")
        for change in changes:
            print(f"  - {change['description']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())