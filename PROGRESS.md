# PROGRESS

Decision and replanning log. One line per event. The agent appends; the loop reads it.
iter 1 T1: implemented core package (corpus, tokenize, HashingEmbedder, Index, CLI search); EN recall@3=1.0
iter 2 T2: Index.save/load (docs JSON, re-embed on load) + CLI index/--index; persistence tests pass
iter 4 T3: Snowball-style RU stemmer in tokenize (ё→е, Cyrillic-only); RU recall@3=1.0, EN unchanged
