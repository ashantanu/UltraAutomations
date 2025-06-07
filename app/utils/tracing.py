from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
import os

LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST")

langfuse = Langfuse(
  secret_key=LANGFUSE_SECRET_KEY,
  public_key=LANGFUSE_PUBLIC_KEY,
  host=LANGFUSE_HOST
)

langfuse_handler = CallbackHandler(
    public_key=LANGFUSE_PUBLIC_KEY,
)