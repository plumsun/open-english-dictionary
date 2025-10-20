from pathlib import Path
from wordfreq import top_n_list

def build_words_list(path: str = 'words.txt') -> None:
  file = Path(path)
  if not file.exists():
    words = top_n_list('en', 26000)
    file.write_text('\n'.join(words))

build_words_list()