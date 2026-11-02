import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["PAYPAL_MOCK"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./test_vaultpay.db"
