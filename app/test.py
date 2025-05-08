import bcrypt

# --- Generate a new hash for a known password ---
plain_password_to_hash = "pass1234"
password_bytes_to_hash = plain_password_to_hash.encode('utf-8')
salt = bcrypt.gensalt(10) # Using fixed rounds for testing consistency
hashed_bytes_generated = bcrypt.hashpw(password_bytes_to_hash, salt)
hashed_password_generated_str = hashed_bytes_generated.decode('utf-8')
print(f"--- Hash Generation ---")
print(f"Password to hash: '{plain_password_to_hash}'")
print(f"Generated Hash:   {hashed_password_generated_str}")
print("-----------------------")

# --- Verify a known password against a specific hash ---
plain_password_to_verify = "pass1234"
# Hash from your database for isfescii@gmail.com
stored_hash_to_verify = "$2b$10$9bQzNR74glqOk2c3s.30Te6TM5NXRPYCCbj8aGdrpSWBRRkS34ULC"

print(f"--- Hash Verification ---")
print(f"Password to verify: '{plain_password_to_verify}'")
print(f"Stored Hash:        {stored_hash_to_verify}")

try:
    plain_bytes = plain_password_to_verify.encode('utf-8')
    stored_hash_bytes = stored_hash_to_verify.encode('utf-8')
    is_match = bcrypt.checkpw(plain_bytes, stored_hash_bytes)
    print(f"Verification Result: {is_match}") 
except ValueError as e:
    print(f"Verification Error: {e} (Likely invalid hash format)")
except Exception as e:
    print(f"An unexpected error occurred during verification: {e}")
print("-----------------------")
