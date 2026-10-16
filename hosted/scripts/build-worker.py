"""Assemble one deployable ESM file; no runtime relative-module resolution needed."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
source = (root / 'worker/index.js').read_text()
bundle = (root / 'worker/intake-bundle.js').read_text().replace('export const INTAKE', 'const INTAKE')
marker = "import { INTAKE } from './intake-bundle.js';"
assert source.count(marker) == 1
(root / 'dist/server/index.js').write_text(source.replace(marker, bundle))
