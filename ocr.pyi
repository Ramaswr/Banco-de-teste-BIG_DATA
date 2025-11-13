
from typing import Union, List, Dict, Any

import io



def image_to_text(image_file: Union[str, bytes, io.IOBase]) -> str: ...

def pdf_to_tables_csv(pdf_file: Union[str, bytes, io.IOBase], output_dir: str, prefix: str = "") -> List[str]: ...

def save_text_as_csv_for_user(username: str, text: str, out_dir: str = "secure_uploads") -> str: ...

