"""
Holding Statement Intelligence POC

Architecture:
  interfaces/   — ports (StorageService, ...)
  services/     — adapters (LocalStorageService today; S3 later)
  pipeline/     — processing (independent of storage backend)
  sample_data/  — input
  output/       — output
"""
