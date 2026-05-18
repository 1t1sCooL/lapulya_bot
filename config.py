import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
HIBP_API_KEY = os.getenv("HIBP_API_KEY", "")
VK_TOKEN = os.getenv("VK_TOKEN", "")
SHODAN_API_KEY = os.getenv("SHODAN_API_KEY", "")

# Breach / leak DB APIs
LEAKCHECK_API_KEY = os.getenv("LEAKCHECK_API_KEY", "")
INTELX_API_KEY = os.getenv("INTELX_API_KEY", "")
DEHASHED_EMAIL = os.getenv("DEHASHED_EMAIL", "")
DEHASHED_API_KEY = os.getenv("DEHASHED_API_KEY", "")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")   # для BreachDirectory
GETCONTACT_TOKEN = os.getenv("GETCONTACT_TOKEN", "")  # неофициальный API GetContact
FACEPP_API_KEY = os.getenv("FACEPP_API_KEY", "")
FACEPP_API_SECRET = os.getenv("FACEPP_API_SECRET", "")

# IP / domain intelligence
GREYNOISE_API_KEY = os.getenv("GREYNOISE_API_KEY", "")   # free: 500/мес — https://viz.greynoise.io/signup
ABUSEIPDB_API_KEY = os.getenv("ABUSEIPDB_API_KEY", "")   # free: 1500/мес — https://www.abuseipdb.com/register

# Email intelligence
EMAILREP_API_KEY  = os.getenv("EMAILREP_API_KEY", "")    # необязателен, 100/день без ключа
HUNTER_API_KEY    = os.getenv("HUNTER_API_KEY", "")      # free: 100/мес — https://hunter.io/users/sign_up
IPQS_API_KEY      = os.getenv("IPQS_API_KEY", "")        # free: 500/мес — https://www.ipqualityscore.com/create-account

_allowed = os.getenv("ALLOWED_USERS", "")
ALLOWED_USERS: set[int] = {int(u) for u in _allowed.split(",") if u.strip().isdigit()}

REQUEST_TIMEOUT = 15
