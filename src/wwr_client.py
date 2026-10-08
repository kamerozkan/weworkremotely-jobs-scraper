"""WeWorkRemotely RSS feed client for remote tech job leads extraction."""
import datetime
import html
import logging
import re
import xml.etree.ElementTree as ET
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class WeWorkRemotelyClient:
    FEED_URL = "https://weworkremotely.com/remote-jobs.rss"

    def __init__(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        self.client = httpx.Client(headers=headers, timeout=20)

    def fetch_jobs(self, max_items=30, keyword_filter="", category_filter=""):
        logging.info("Querying WeWorkRemotely RSS: %s", self.FEED_URL)
        resp = self.client.get(self.FEED_URL)
        if resp.status_code != 200:
            logging.error("Failed to fetch WeWorkRemotely RSS (HTTP %s)", resp.status_code)
            return []

        try:
            root = ET.fromstring(resp.text)
        except Exception as e:
            logging.error("XML parse error on WWR feed: %s", e)
            return []

        channel = root.find("channel")
        raw_items = channel.findall("item") if channel is not None else []
        logging.info("Discovered %d active listings on WeWorkRemotely", len(raw_items))

        kw_clean = keyword_filter.strip().lower() if keyword_filter else ""
        cat_clean = category_filter.strip().lower() if category_filter else ""
        jobs = []

        for it in raw_items:
            if len(jobs) >= max_items:
                break

            title_elem = it.find("title")
            title_raw = title_elem.text.strip() if title_elem is not None and title_elem.text else ""

            if ":" in title_raw:
                comp, pos = title_raw.split(":", 1)
                company, position = comp.strip(), pos.strip()
            else:
                company, position = "Company", title_raw.strip()

            cat_elem = it.find("category")
            category = cat_elem.text.strip() if cat_elem is not None and cat_elem.text else "Remote"

            reg_elem = it.find("region")
            region = reg_elem.text.strip() if reg_elem is not None and reg_elem.text else "Anywhere in the World"

            typ_elem = it.find("type")
            emp_type = typ_elem.text.strip() if typ_elem is not None and typ_elem.text else "Full-Time"

            link_elem = it.find("link")
            link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""

            desc_elem = it.find("description")
            desc_html = desc_elem.text if desc_elem is not None and desc_elem.text else ""

            logo = ""
            if '<img' in desc_html and 'src="' in desc_html:
                logo = desc_html.split('src="', 1)[1].split('"', 1)[0]
            elif '<img' in desc_html and "src='" in desc_html:
                logo = desc_html.split("src='", 1)[1].split("'", 1)[0]

            clean_desc = re.sub(r"<[^>]+>", " ", desc_html)
            clean_desc = html.unescape(" ".join(clean_desc.split()))

            if kw_clean:
                search_text = f"{position} {company} {category} {clean_desc}".lower()
                if kw_clean not in search_text:
                    continue

            if cat_clean:
                if cat_clean not in category.lower():
                    continue

            pub_elem = it.find("pubDate")
            pub_date = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else ""

            job_item = {
                "id": link or f"{company}-{position}",
                "company": company,
                "position": position,
                "category": category,
                "region": region,
                "type": emp_type,
                "url": link,
                "applyUrl": link,
                "companyLogo": logo,
                "summary": clean_desc[:300] + "..." if len(clean_desc) > 300 else clean_desc,
                "fullDescription": clean_desc,
                "postedAt": pub_date,
                "extractedAt": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            jobs.append(job_item)
            logging.info("Extracted WeWorkRemotely job: %s @ %s (%s - %s)", position, company, category, region)

        logging.info("Total WeWorkRemotely jobs extracted: %d", len(jobs))
        return jobs
