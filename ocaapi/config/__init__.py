from dotenv import load_dotenv
import os
OCA_API_ENV_FILE = os.environ.get("OCA_API_ENV_FILE",".env")

if os.path.isfile(OCA_API_ENV_FILE):
    load_dotenv(OCA_API_ENV_FILE)

OCA_API_MONGODB_URI         = os.environ.get("OCA_API_MONGODB_URI","mongodb://oca:d22a75e9e729debc@localhost:27017/ocadb?authSource=admin")
OCA_API_MONGODB_DATABASE_NAME = os.environ.get("OCA_API_MONGODB_DATABASE_NAME","ocadb")


