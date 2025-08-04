import asyncio
import hashlib
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urljoin, urlparse
from contextlib import asynccontextmanager
import aiohttp
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from ..database.connection import get_db
from ..database.models import Agency, Form, FormChange, MonitoringRun
from ..utils.config_loader import load_agency_config, get_monitoring_settings

logger = logging.getLogger(__name__)


class WebDriverPool:
    """Pool for managing WebDriver instances."""
    
    def __init__(self, max_drivers: int = 3):
        self.max_drivers = max_drivers
        self.drivers: List[webdriver.Chrome] = []
        self.available_drivers: List[webdriver.Chrome] = []
        self._lock = asyncio.Lock()
    
    async def get_driver(self) -> Optional[webdriver.Chrome]:
        """Get an available WebDriver instance."""
        async with self._lock:
            if self.available_drivers:
                return self.available_drivers.pop()
            
            if len(self.drivers) < self.max_drivers:
                driver = self._create_driver()
                if driver:
                    self.drivers.append(driver)
                    return driver
            
            return None
    
    async def return_driver(self, driver: webdriver.Chrome) -> None:
        """Return a WebDriver instance to the pool."""
        async with self._lock:
            if driver in self.drivers and driver not in self.available_drivers:
                self.available_drivers.append(driver)
    
    def _create_driver(self) -> Optional[webdriver.Chrome]:
        """Create a new WebDriver instance."""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")
            chrome_options.add_argument("--disable-javascript")  # Only if not needed
            chrome_options.add_argument("--user-agent=PayrollMonitor/1.0 (Government Forms Monitoring)")
            
            # Use webdriver-manager to handle driver installation
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(10)
            
            logger.debug("Created new WebDriver instance")
            return driver
            
        except Exception as e:
            logger.error(f"Failed to create WebDriver: {e}")
            return None
    
    async def cleanup(self) -> None:
        """Clean up all WebDriver instances."""
        async with self._lock:
            for driver in self.drivers:
                try:
                    driver.quit()
                except Exception as e:
                    logger.error(f"Error closing WebDriver: {e}")
            
            self.drivers.clear()
            self.available_drivers.clear()
            logger.info("WebDriver pool cleaned up")


class WebScraper:
    """Core web scraping class for monitoring government websites."""
    
    def __init__(self, user_agent: Optional[str] = None, timeout: int = 30, max_retries: int = 3):
        self.user_agent = user_agent or "PayrollMonitor/1.0 (Government Forms Monitoring)"
        self.timeout = timeout
        self.max_retries = max_retries
        self.session: Optional[aiohttp.ClientSession] = None
        self.driver_pool = WebDriverPool()
        
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
        await self.driver_pool.cleanup()
    
    async def fetch_page_content(self, url: str, use_selenium: bool = False) -> Tuple[str, int, Dict[str, Any]]:
        """
        Fetch page content using either aiohttp or Selenium with retry logic.
        
        Args:
            url: URL to fetch
            use_selenium: Whether to use Selenium for JavaScript-heavy sites
            
        Returns:
            Tuple of (content, status_code, metadata)
        """
        metadata = {
            "url": url,
            "timestamp": datetime.utcnow().isoformat(),
            "method": "selenium" if use_selenium else "aiohttp",
            "retries": 0
        }
        
        for attempt in range(self.max_retries + 1):
            try:
                if use_selenium:
                    return await self._fetch_with_selenium(url, metadata)
                else:
                    return await self._fetch_with_aiohttp(url, metadata)
                    
            except Exception as e:
                metadata["retries"] = attempt
                metadata["error"] = str(e)
                
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed for {url}: {e}")
                    return "", 0, metadata
    
    async def _fetch_with_aiohttp(self, url: str, metadata: Dict[str, Any]) -> Tuple[str, int, Dict[str, Any]]:
        """Fetch content using aiohttp."""
        if not self.session:
            raise RuntimeError("aiohttp session not initialized")
        
        try:
            async with self.session.get(url) as response:
                content = await response.text()
                metadata.update({
                    "status_code": response.status,
                    "content_type": response.headers.get("content-type", ""),
                    "content_length": len(content),
                    "last_modified": response.headers.get("last-modified", ""),
                    "final_url": str(response.url)
                })
                return content, response.status, metadata
                
        except asyncio.TimeoutError:
            metadata["error"] = "Timeout"
            return "", 408, metadata
        except Exception as e:
            metadata["error"] = str(e)
            return "", 0, metadata
    
    async def _fetch_with_selenium(self, url: str, metadata: Dict[str, Any]) -> Tuple[str, int, Dict[str, Any]]:
        """Fetch content using Selenium for JavaScript-heavy sites."""
        driver = await self.driver_pool.get_driver()
        if not driver:
            metadata["error"] = "No WebDriver available"
            return "", 0, metadata
        
        try:
            driver.get(url)
            
            # Wait for page to load
            WebDriverWait(driver, self.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            content = driver.page_source
            metadata.update({
                "status_code": 200,
                "content_length": len(content),
                "current_url": driver.current_url
            })
            
            return content, 200, metadata
            
        except TimeoutException:
            metadata["error"] = "Timeout"
            return "", 408, metadata
        except WebDriverException as e:
            metadata["error"] = str(e)
            return "", 0, metadata
        finally:
            await self.driver_pool.return_driver(driver)
    
    def extract_form_links(self, content: str, base_url: str) -> List[Dict[str, Any]]:
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
    
    def detect_changes(self, old_content: str, new_content: str) -> List[Dict[str, Any]]:
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
        self.scraper: Optional[WebScraper] = None
        self.monitoring_settings = get_monitoring_settings()
        
    async def monitor_agency(self, agency_id: int) -> List[Dict[str, Any]]:
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
                async with WebScraper(
                    timeout=self.monitoring_settings.get('timeout_seconds', 30),
                    max_retries=self.monitoring_settings.get('retry_attempts', 3)
                ) as scraper:
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
    
    async def _monitor_form(self, form: Form, db) -> List[Dict[str, Any]]:
        """Monitor a specific form for changes."""
        changes = []
        
        try:
            # Determine if we need Selenium based on form characteristics
            use_selenium = self._should_use_selenium(form)
            
            # Fetch current content
            content, status_code, metadata = await self.scraper.fetch_page_content(
                form.form_url or form.agency.base_url,
                use_selenium=use_selenium
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
                    # Content has changed - create change record
                    change = FormChange(
                        form_id=form.id,
                        change_type="content",
                        change_description="Form content has been modified",
                        new_value=content_hash,
                        old_value=last_run.content_hash,
                        change_hash=content_hash,
                        severity=self._determine_severity(form, content_hash, last_run.content_hash)
                    )
                    db.add(change)
                    changes.append({
                        'form_id': form.id,
                        'form_name': form.name,
                        'change_type': 'content',
                        'description': 'Form content has been modified',
                        'severity': change.severity
                    })
            
            # Create new monitoring run for this form
            form_run = MonitoringRun(
                agency_id=form.agency_id,
                form_id=form.id,
                status="completed",
                completed_at=datetime.utcnow(),
                content_hash=content_hash,
                http_status_code=status_code,
                response_time_ms=int(metadata.get('response_time_ms', 0))
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
    
    def _should_use_selenium(self, form: Form) -> bool:
        """Determine if Selenium should be used for this form."""
        # Use Selenium for forms that likely have JavaScript
        selenium_indicators = [
            'portal', 'dynamic', 'javascript', 'spa', 'react', 'angular'
        ]
        
        form_url = form.form_url or form.agency.base_url
        form_name = form.name.lower()
        
        return any(indicator in form_url.lower() or indicator in form_name 
                  for indicator in selenium_indicators)
    
    def _determine_severity(self, form: Form, new_hash: str, old_hash: str) -> str:
        """Determine the severity of a change."""
        # Simple heuristic - in production, use AI analysis
        if form.name in ['WH-347', 'A1-131']:  # Critical federal forms
            return 'high'
        elif form.agency.agency_type == 'federal':
            return 'medium'
        else:
            return 'low'
    
    async def monitor_all_agencies(self) -> Dict[str, List[Dict[str, Any]]]:
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