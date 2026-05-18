import asyncio
import whois
import dns.resolver
import dns.reversename
import httpx
from config import REQUEST_TIMEOUT


async def whois_lookup(domain: str) -> dict:
    loop = asyncio.get_event_loop()
    try:
        data = await loop.run_in_executor(None, whois.whois, domain)
        return {
            "registrar": data.registrar,
            "creation_date": _fmt_date(data.creation_date),
            "expiration_date": _fmt_date(data.expiration_date),
            "updated_date": _fmt_date(data.updated_date),
            "name_servers": _normalize_list(data.name_servers),
            "status": _normalize_list(data.status),
            "emails": _normalize_list(data.emails),
            "org": data.org,
            "country": data.country,
        }
    except Exception as e:
        return {"error": str(e)}


async def dns_lookup(domain: str) -> dict:
    loop = asyncio.get_event_loop()
    result = {}
    record_types = ["A", "AAAA", "MX", "TXT", "NS", "CNAME", "SOA"]
    for rtype in record_types:
        try:
            answers = await loop.run_in_executor(
                None, lambda d=domain, r=rtype: dns.resolver.resolve(d, r, raise_on_no_answer=False)
            )
            records = [str(r) for r in answers]
            if records:
                result[rtype] = records
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.DNSException):
            pass
        except Exception:
            pass
    return result


async def get_ip_geolocation(ip: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(f"https://ipapi.co/{ip}/json/")
            if r.status_code == 200:
                data = r.json()
                return {
                    "ip": data.get("ip"),
                    "city": data.get("city"),
                    "region": data.get("region"),
                    "country": data.get("country_name"),
                    "org": data.get("org"),
                    "asn": data.get("asn"),
                    "timezone": data.get("timezone"),
                    "latitude": data.get("latitude"),
                    "longitude": data.get("longitude"),
                }
    except Exception as e:
        return {"error": str(e)}
    return {}


async def get_ssl_info(domain: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, verify=False) as client:
            r = await client.get(f"https://crt.sh/?q={domain}&output=json")
            if r.status_code == 200:
                certs = r.json()
                names = sorted({c["name_value"] for c in certs[:100]})
                return {"subdomains": names[:50], "total_certs": len(certs)}
    except Exception:
        pass
    return {}


def _fmt_date(d) -> str:
    if isinstance(d, list):
        d = d[0]
    if d is None:
        return ""
    return str(d)[:10] if hasattr(d, "__str__") else ""


def _normalize_list(val) -> list[str]:
    if val is None:
        return []
    if isinstance(val, str):
        return [val]
    return [str(v) for v in val if v]
