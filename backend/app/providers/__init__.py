"""Mock financial-data providers (stand-ins for FDX data providers / banks).

Populated in **Items 3-4**:
- Item 3: a mock bank that returns FDX-shaped JSON behind a mock OAuth2 flow —
  the clean, standards-native source.
- Item 4: a second source with a deliberately messy schema, so the normalizer
  has something hard to map.
"""
