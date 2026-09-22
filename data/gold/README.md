# Gold labels (referência)

Arquivo `labels-ai-draft-v2.csv` importado do projeto [inference-triage](https://github.com/) como referência **não-oficial** para benchmark determinístico.

- **Join key:** `sample_id` ↔ `id` da reclamação
- **Integridade:** `source_text_hash` (scheme `canonical-text-v1`)
- **Campos comparáveis (nível 1):** `category`, `product`, `sentiment`, `urgency`
- **Campos comparáveis (nível 2):** acima + `risk`

Use com `python main.py --benchmark --gold data/gold/labels-ai-draft-v2.csv`.
