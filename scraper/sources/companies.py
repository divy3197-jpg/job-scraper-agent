"""
Registry of major companies (IIM A/B/C summer + final placement recruiters) whose
career portals expose a usable API, grouped by ATS platform. Add a line here to
cover a new company — no new code needed.

Platforms:
  workday    -> POST /wday/cxs/{tenant}/{site}/jobs
  greenhouse -> GET  boards-api.greenhouse.io/v1/boards/{token}/jobs
  lever      -> GET  api.lever.co/v0/postings/{token}?mode=json
"""

WORKDAY = [
    # (display_name, tenant, site, datacenter)
    ("Mastercard", "mastercard", "CorporateCareers", "wd1"),
    ("Adobe", "adobe", "external_experienced", "wd5"),
    ("Citi", "citi", "2", "wd5"),
    ("Unilever", "unilever", "Unilever_Experienced_Professionals", "wd3"),
]

GREENHOUSE = [
    # (display_name, board_token)
    ("Stripe", "stripe"),
    ("Airbnb", "airbnb"),
    ("Groww", "groww"),
    ("PhonePe", "phonepe"),
    ("Postman", "postman"),
    ("HighRadius", "highradius"),
    ("Druva", "druva"),
]

LEVER = [
    # (display_name, board_token)
    ("Meesho", "meesho"),
    ("CRED", "cred"),
    ("FamPay", "fampay"),
]
