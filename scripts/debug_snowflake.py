"""
scripts/debug_snowflake.py
Connect with minimal params to check user identity, grants, and roles.
"""
import os
import snowflake.connector
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization

load_dotenv()

key_path = os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"]
with open(key_path, "rb") as fh:
    key = serialization.load_pem_private_key(fh.read(), password=None)
pk = key.private_bytes(
    serialization.Encoding.DER,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
)

print(f"Connecting to {os.environ['SNOWFLAKE_ACCOUNT']} as user {os.environ['SNOWFLAKE_USER']} without specifying role/warehouse...")
try:
    con = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        private_key=pk,
    )
    cur = con.cursor()
    cur.execute("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_AVAILABLE_ROLES()")
    print("User info:", cur.fetchone())
    
    cur.execute("SHOW GRANTS TO USER SVC_INGEST")
    print("\nGrants to SVC_INGEST:")
    for row in cur.fetchall():
        print(row)
        
    cur.close()
    con.close()
except Exception as e:
    print("Error:", e)

