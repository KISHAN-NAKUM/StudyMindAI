"""Global pytest configuration."""
import os
import torch  # Ensure PyTorch C++ runtime is initialized before pytest AST transformations

# Enforce offline question bank for unit tests to avoid network latency / timeouts
os.environ["LLM_PROVIDER"] = "offline"
