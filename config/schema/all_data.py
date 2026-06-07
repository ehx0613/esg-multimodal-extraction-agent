from .e_data import E_SCHEMA_DATA
from .g_data import G_SCHEMA_DATA
from .qualitative_data import QUALITATIVE_SCHEMA_DATA
from .s_data import S_SCHEMA_DATA


ALL_SCHEMA_DATA = [
    *E_SCHEMA_DATA,
    *S_SCHEMA_DATA,
    *G_SCHEMA_DATA,
    *QUALITATIVE_SCHEMA_DATA,
]

__all__ = ["ALL_SCHEMA_DATA"]
