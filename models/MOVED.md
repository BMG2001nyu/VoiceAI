# models/ moved

All model clients are now in **`backend/models/`**.

- `backend/models/lite_client.py` — Nova 2 Lite chat / planning client
- `backend/models/sonic_client.py` — Nova 2 Sonic real-time voice client
- `backend/models/sonic_tools.py` — Sonic tool schemas (5 tools)

Import from inside the backend package:
```python
from models.lite_client import LiteClient
from models.sonic_client import SonicClient
from models.sonic_tools import SONIC_TOOLS
```
